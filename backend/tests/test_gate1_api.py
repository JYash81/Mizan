"""Integration tests for Masking Runs, Finding Reviews, and Gate 1 Human Approvals."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.dataset import DatasetVersionStatus
from app.models.identity import AccountStatus, User
from app.models.organization import OrganizationRole, WorkspaceRole
from app.modules.auth.services import password_service, session_service
from app.modules.datasets.services import dataset_service
from app.modules.masking.approval.gate1_service import require_gate1_approval
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def gate1_test_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db

    tmp_dir = tempfile.TemporaryDirectory()
    storage = LocalStorageProvider(tmp_dir.name)
    set_storage_provider_override(storage)

    client = TestClient(app)

    db = Session(engine, expire_on_commit=False)

    # Lead user (Workspace Owner)
    owner = User(
        full_name="Fatima Lead",
        email="fatima@mizan.ae",
        normalized_email="fatima@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    # Junior user (Workspace Member without approve permission)
    member = User(
        full_name="Tariq Member",
        email="tariq@mizan.ae",
        normalized_email="tariq@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([owner, member])
    db.commit()

    owner_sess = session_service.create_session(db, owner.id)
    member_sess = session_service.create_session(db, member.id)
    db.commit()

    org, _ = organization_service.create_organization(db, owner.id, "Mizan Corp", "mizan-corp")
    ws, _ = workspace_service.create_workspace(db, org.id, owner.id, "AI Lab", "ai-lab")

    # Add member to org and workspace
    organization_service.add_organization_member(
        db, org.id, member.id, OrganizationRole.MEMBER, invited_by=owner.id
    )
    workspace_service.add_workspace_member(
        db, ws.id, member.id, WorkspaceRole.WORKSPACE_MEMBER, actor_id=owner.id
    )
    db.commit()

    yield {
        "client": client,
        "engine": engine,
        "owner": owner,
        "member": member,
        "org_id": org.id,
        "ws_id": ws.id,
        "storage": storage,
        "owner_cookies": {"mizan_session": owner_sess.session_token},
        "owner_headers": {"X-CSRF-Token": owner_sess.csrf_token},
        "member_cookies": {"mizan_session": member_sess.session_token},
        "member_headers": {"X-CSRF-Token": member_sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_gate1_full_lifecycle(gate1_test_env):
    client = gate1_test_env["client"]
    ws_id = gate1_test_env["ws_id"]
    owner_cookies = gate1_test_env["owner_cookies"]
    owner_headers = gate1_test_env["owner_headers"]
    member_cookies = gate1_test_env["member_cookies"]
    member_headers = gate1_test_env["member_headers"]
    storage = gate1_test_env["storage"]
    engine = gate1_test_env["engine"]

    db = Session(engine, expire_on_commit=False)

    # 1. Create dataset and document
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "UAE Customer Data", "slug": "uae-cust"},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert ds_resp.status_code == 201
    ds_data = ds_resp.json()
    dataset_id = ds_data["dataset"]["id"]
    version_id = ds_data["version"]["id"]

    # Upload document with UAE PII
    sample_text = (
        "Customer Agreement:\n"
        "Name: Khalid Mansoor\n"
        "Emirates ID: 784-1985-1234567-1\n"
        "IBAN: AE140330000000000000000\n"
        "Mobile: +971 50 123 4567\n"
        "Email: khalid@mizan.ae"
    )
    upload_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        files={"file": ("customer.txt", sample_text.encode("utf-8"), "text/plain")},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    # Finalize version to READY
    ver = db.query(dataset_service.DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "abc123sourcehash"
    db.commit()

    # 2. Trigger Masking Run
    run_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    run_id = run_data["id"]
    assert run_data["status"] == "COMPLETED"
    assert run_data["findings_count"] > 0
    assert run_data["masked_output_digest"] is not None

    # 3. List findings
    find_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/findings",
        cookies=owner_cookies,
    )
    assert find_resp.status_code == 200
    findings = find_resp.json()
    assert len(findings) >= 3
    entity_types = {f["entity_type"] for f in findings}
    assert "UAE_EMIRATES_ID" in entity_types
    assert "UAE_IBAN" in entity_types
    assert "UAE_PHONE_NUMBER" in entity_types

    # 4. Add manual finding
    manual_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/findings/manual",
        json={
            "document_id": doc_id,
            "entity_type": "ORGANIZATION_INTERNAL_CODE",
            "start_offset": 0,
            "end_offset": 8,
        },
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert manual_resp.status_code == 201
    assert manual_resp.json()["is_manual"] is True

    # 5. Review document content (original vs masked preview)
    review_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/documents/{doc_id}/review",
        cookies=owner_cookies,
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert "784-1985-1234567-1" in review_data["original_text"]
    assert "[UAE_EMIRATES_ID]" in review_data["masked_preview"]

    # 6. RBAC Guard: Member cannot approve Gate 1 (403 Forbidden)
    member_approve_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "Attempting unauthorized approval"},
        cookies=member_cookies,
        headers=member_headers,
    )
    assert member_approve_resp.status_code == 403

    # 7. Owner approves Gate 1
    approve_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "All UAE identifiers confirmed and masked."},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert approve_resp.status_code == 201
    approval_data = approve_resp.json()
    approval_id = approval_data["id"]
    assert approval_data["decision"] == "APPROVED"
    assert approval_data["signature_algorithm"] == "Ed25519"
    assert len(approval_data["approval_signature"]) == 128

    # 8. Cryptographic verification endpoint
    verify_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/gate1/approvals/{approval_id}/verify",
        cookies=owner_cookies,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_valid"] is True

    # 9. Downstream require_gate1_approval guard check
    approval_obj = require_gate1_approval(db, ws_id, version_id, storage)
    assert approval_obj.id == approval_id


def test_ocr_safety_guard_blocks_approval(gate1_test_env):
    client = gate1_test_env["client"]
    ws_id = gate1_test_env["ws_id"]
    owner_cookies = gate1_test_env["owner_cookies"]
    owner_headers = gate1_test_env["owner_headers"]
    engine = gate1_test_env["engine"]

    db = Session(engine, expire_on_commit=False)

    # Create dataset
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        json={"name": "Scanned Forms", "slug": "scanned-forms"},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    dataset_id = ds_resp.json()["dataset"]["id"]
    version_id = ds_resp.json()["version"]["id"]

    # Upload empty scanned PDF (simulating image-only scan needing OCR)
    upload_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        files={"file": ("scan.pdf", b"%PDF-1.4 empty scan", "application/pdf")},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert upload_resp.status_code == 201

    # Mark doc char_count = 0 and version ready
    ver = db.query(dataset_service.DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "scannedhash"
    db.commit()

    # Trigger run
    run_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    run_id = run_resp.json()["id"]
    assert run_resp.json()["extraction_coverage"] == "OCR_REQUIRED"

    # Attempt Gate 1 approval without justification -> FAILS with 400
    blocked_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "Approving without OCR check"},
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert blocked_resp.status_code == 400
    error_msg = blocked_resp.json().get("error", {}).get("message") or blocked_resp.json().get(
        "detail", ""
    )
    assert "OCR_REQUIRED" in error_msg

    # With authorized override justification -> SUCCEEDS
    override_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/masking-runs/{run_id}/gate1/approve",
        json={
            "decision_reason": "Manually inspected physical document",
            "override_coverage_reason": "Visual inspection verified zero personal data on blank template form",
        },
        cookies=owner_cookies,
        headers=owner_headers,
    )
    assert override_resp.status_code == 201
    assert override_resp.json()["decision"] == "APPROVED"
