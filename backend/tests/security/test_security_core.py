"""Security Regression Test Suite: Core Scenarios (SEC-001 through SEC-020).

Covers authentication, tenant boundary enforcement, RBAC, mass assignment,
session and token lifecycle, path traversal, decompression bombs, PII handling,
cryptographic attestation, signature purpose separation, separation of duties,
artifact validation, and RAG isolation.
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.artifact_registry import (
    Gate3Decision,
    ModelFamily,
    ModelVersion,
    ModelVersionStatus,
)
from app.models.identity import AccountStatus, User
from app.models.masking import (
    FindingStatus,
    MaskingStrategy,
)
from app.models.organization import (
    OrganizationMembership,
    OrganizationRole,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.models.runtime import (
    CustomerSite,
    SiteStatus,
)
from app.modules.artifact_registry.exceptions import (
    SeparationOfDutiesViolationError,
    SignaturePurposeMismatchError,
)
from app.modules.artifact_registry.gate3_service import (
    submit_gate3_decision,
    verify_gate3_attestation,
)
from app.modules.auth.services import password_service, session_service
from app.modules.documents.services.file_validator import (
    DecompressionBombDetectedError,
    FileFormatUnsupportedError,
    validate_file_upload,
)
from app.modules.masking.cryptography.signing_service import (
    SignatureVerificationError,
    sign_payload,
    verify_signature,
)
from app.modules.masking.services.masking_service import mask_text
from app.modules.storage.local import LocalStorageProvider
from app.modules.storage.provider import StorageBucket, StorageSecurityError
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def sec_core_env(tmp_path):
    """Sets up a fully isolated in-memory test environment for security core tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    db = Session(engine, expire_on_commit=False)

    # Tenant A User (Alice - Owner)
    user_a = User(
        id=f"usr-a-{uuid.uuid4().hex[:6]}",
        full_name="Alice Owner",
        email="alice@tenanta.com",
        normalized_email="alice@tenanta.com",
        password_hash=password_service.hash_password("StrongPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    # Tenant A Member (Charlie - regular member)
    user_c = User(
        id=f"usr-c-{uuid.uuid4().hex[:6]}",
        full_name="Charlie Member",
        email="charlie@tenanta.com",
        normalized_email="charlie@tenanta.com",
        password_hash=password_service.hash_password("StrongPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    # Tenant B User (Bob - foreign tenant)
    user_b = User(
        id=f"usr-b-{uuid.uuid4().hex[:6]}",
        full_name="Bob Foreign",
        email="bob@tenantb.com",
        normalized_email="bob@tenantb.com",
        password_hash=password_service.hash_password("StrongPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([user_a, user_b, user_c])
    db.commit()

    org_a, _ = organization_service.create_organization(db, user_a.id, "Tenant A Corp", "tenant-a")
    ws_a, _ = workspace_service.create_workspace(db, org_a.id, user_a.id, "Workspace Alpha", "ws-alpha")

    # Add Charlie as MEMBER in ws_a
    db.add(OrganizationMembership(
        organization_id=org_a.id,
        user_id=user_c.id,
        role=OrganizationRole.MEMBER,
    ))
    db.add(WorkspaceMembership(
        workspace_id=ws_a.id,
        user_id=user_c.id,
        role=WorkspaceRole.WORKSPACE_MEMBER,
    ))

    org_b, _ = organization_service.create_organization(db, user_b.id, "Tenant B Corp", "tenant-b")
    ws_b, _ = workspace_service.create_workspace(db, org_b.id, user_b.id, "Workspace Beta", "ws-beta")
    db.commit()

    sess_a = session_service.create_session(db, user_a.id)
    sess_b = session_service.create_session(db, user_b.id)
    sess_c = session_service.create_session(db, user_c.id)
    db.commit()

    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    storage = LocalStorageProvider(storage_dir)

    return {
        "engine": engine,
        "client": client,
        "user_a": user_a,
        "user_b": user_b,
        "user_c": user_c,
        "org_a": org_a,
        "ws_a": ws_a,
        "org_b": org_b,
        "ws_b": ws_b,
        "sess_a": sess_a,
        "sess_b": sess_b,
        "sess_c": sess_c,
        "storage": storage,
    }


# =========================================================================
# SEC-001: Unauthenticated Protected Endpoint Access
# =========================================================================
def test_sec_001_unauthenticated_access_rejected(sec_core_env):
    """Protected endpoints must reject requests with 401 when no session cookie is provided."""
    client = sec_core_env["client"]
    ws_a_id = sec_core_env["ws_a"].id

    endpoints = [
        ("GET", f"/api/v1/workspaces/{ws_a_id}"),
        ("GET", f"/api/v1/workspaces/{ws_a_id}/datasets"),
        ("GET", f"/api/v1/workspaces/{ws_a_id}/artifact-registry/families"),
        ("GET", f"/api/v1/workspaces/{ws_a_id}/sites"),
        ("GET", "/api/v1/ops/incidents"),
        ("POST", f"/api/v1/workspaces/{ws_a_id}/datasets"),
    ]

    for method, endpoint in endpoints:
        if method == "GET":
            resp = client.get(endpoint)
        else:
            resp = client.post(endpoint, json={"name": "test"})
        assert resp.status_code == 401, f"Expected 401 on {endpoint}, got {resp.status_code}"


# =========================================================================
# SEC-002: Cross-Tenant Resource Access (Anti-Enumeration 404)
# =========================================================================
def test_sec_002_cross_tenant_resource_access_anti_enumeration(sec_core_env):
    """Accessing foreign tenant resources must return 404 Not Found to prevent enumeration."""
    client = sec_core_env["client"]
    sess_b = sec_core_env["sess_b"]
    org_a = sec_core_env["org_a"]
    ws_a = sec_core_env["ws_a"]

    cookies_b = {"mizan_session": sess_b.session_token}

    # Bob (Tenant B) attempts to read Tenant A resources
    assert client.get(f"/api/v1/organizations/{org_a.id}", cookies=cookies_b).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_a.id}", cookies=cookies_b).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_a.id}/datasets", cookies=cookies_b).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_a.id}/models", cookies=cookies_b).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_a.id}/sites", cookies=cookies_b).status_code == 404


# =========================================================================
# SEC-003: Workspace Privilege Escalation (RBAC)
# =========================================================================
def test_sec_003_workspace_privilege_escalation_rejected(sec_core_env):
    """Member role attempting workspace administrative actions must be rejected with 403."""
    client = sec_core_env["client"]
    sess_c = sec_core_env["sess_c"]  # Charlie is WORKSPACE_MEMBER
    ws_a = sec_core_env["ws_a"]

    cookies_c = {"mizan_session": sess_c.session_token}
    headers_c = {"X-CSRF-Token": sess_c.csrf_token}

    # Charlie attempts to update workspace settings (requires WORKSPACE_ADMIN / OWNER)
    resp = client.patch(
        f"/api/v1/workspaces/{ws_a.id}",
        cookies=cookies_c,
        headers=headers_c,
        json={"name": "Charlie Hijacked Workspace"},
    )
    assert resp.status_code == 403


# =========================================================================
# SEC-004: Object Property Over-Posting / Mass Assignment
# =========================================================================
def test_sec_004_mass_assignment_fields_ignored_or_rejected(sec_core_env):
    """Injected sensitive attributes (is_superuser, role, status) must be ignored or rejected."""
    client = sec_core_env["client"]
    sess_a = sec_core_env["sess_a"]
    ws_a = sec_core_env["ws_a"]

    cookies = {"mizan_session": sess_a.session_token}
    headers = {"X-CSRF-Token": sess_a.csrf_token}

    # Attempt to mass-assign unmapped/protected fields in workspace update
    resp = client.patch(
        f"/api/v1/workspaces/{ws_a.id}",
        cookies=cookies,
        headers=headers,
        json={
            "name": "Updated Safe Name",
            "is_superuser": True,
            "role": "SUPERADMIN",
            "organization_id": "org-hacked",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Updated Safe Name"
    # Verify organization_id was not overwritten
    assert data["organization_id"] == sec_core_env["org_a"].id


# =========================================================================
# SEC-005: Expired Session Reuse Rejected
# =========================================================================
def test_sec_005_expired_session_reuse_rejected(sec_core_env):
    """Sessions with expires_at in the past must be rejected with 401."""
    from app.models.identity import AuthSession

    client = sec_core_env["client"]
    engine = sec_core_env["engine"]
    user_a = sec_core_env["user_a"]

    with Session(engine) as db:
        expired_sess = session_service.create_session(db, user_a.id)
        # Manually backdate expiration in database
        stored = db.get(AuthSession, expired_sess.session_id)
        assert stored is not None
        stored.expires_at = datetime.now(UTC) - timedelta(hours=2)
        db.commit()
        expired_token = expired_sess.session_token

    resp = client.get(
        f"/api/v1/workspaces/{sec_core_env['ws_a'].id}",
        cookies={"mizan_session": expired_token},
    )
    assert resp.status_code == 401


# =========================================================================
# SEC-006: CSRF Bypass Without X-CSRF-Token Rejected
# =========================================================================
def test_sec_006_csrf_protection_enforcement(sec_core_env):
    """Mutating state without valid CSRF header must be rejected with 403."""
    client = sec_core_env["client"]
    sess_a = sec_core_env["sess_a"]
    ws_a = sec_core_env["ws_a"]

    cookies = {"mizan_session": sess_a.session_token}

    # POST without X-CSRF-Token
    resp = client.post(
        f"/api/v1/workspaces/{ws_a.id}/datasets",
        cookies=cookies,
        json={"name": "CSRF Attack Dataset", "description": "Should fail"},
    )
    assert resp.status_code == 403

    # POST with mismatched X-CSRF-Token
    resp_bad = client.post(
        f"/api/v1/workspaces/{ws_a.id}/datasets",
        cookies=cookies,
        headers={"X-CSRF-Token": "invalid_csrf_token_value"},
        json={"name": "CSRF Attack Dataset", "description": "Should fail"},
    )
    assert resp_bad.status_code == 403


# =========================================================================
# SEC-007: Password Reset Token Single-Use Replay Prevention
# =========================================================================
def test_sec_007_password_reset_token_single_use(sec_core_env):
    """Password reset token must be invalidated immediately upon first consumption."""
    from app.models.identity import TokenPurpose
    from app.modules.auth.services.token_service import consume_token, create_token

    engine = sec_core_env["engine"]
    user_a = sec_core_env["user_a"]

    with Session(engine) as db:
        issued = create_token(db, user_a.id, TokenPurpose.PASSWORD_RESET)
        db.commit()

        # First consumption succeeds
        consumed = consume_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET)
        db.commit()
        assert consumed is not None
        assert consumed.user_id == user_a.id

        # Replay attempt must fail (returns None)
        replay_result = consume_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET)
        assert replay_result is None


# =========================================================================
# SEC-008: Invitation / Verification Token Single-Use Replay Prevention
# =========================================================================
def test_sec_008_invitation_token_single_use(sec_core_env):
    """Single-use auth tokens must not be accepted multiple times."""
    from app.models.identity import TokenPurpose
    from app.modules.auth.services.token_service import consume_token, create_token

    engine = sec_core_env["engine"]
    user_a = sec_core_env["user_a"]

    with Session(engine) as db:
        issued = create_token(db, user_a.id, TokenPurpose.EMAIL_VERIFICATION)
        db.commit()

        # First consumption
        consumed = consume_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION)
        db.commit()
        assert consumed is not None
        assert consumed.user_id == user_a.id

        # Second consumption attempt must fail
        replayed = consume_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION)
        assert replayed is None


# =========================================================================
# SEC-009: Path Traversal in Storage Provider Rejected
# =========================================================================
def test_sec_009_storage_path_traversal_rejected(sec_core_env):
    """LocalStorageProvider must reject path traversal attempts with StorageSecurityError."""
    storage: LocalStorageProvider = sec_core_env["storage"]

    traversal_keys = [
        "../../etc/passwd",
        "../sibling_bucket/file.txt",
        "valid/../../outside.txt",
        "..\\..\\windows\\system32\\calc.exe",
    ]

    for key in traversal_keys:
        with pytest.raises(StorageSecurityError):
            storage.put_object(StorageBucket.RAW_UPLOADS, key, b"malicious content")

        with pytest.raises(StorageSecurityError):
            storage.get_object(StorageBucket.RAW_UPLOADS, key)


# =========================================================================
# SEC-010: Decompression Bomb & Oversized Archive Rejected
# =========================================================================
def test_sec_010_decompression_bomb_rejected():
    """Archive decompression bombs with extreme compression ratios must be rejected safely."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # 10 MB of zeros compresses to ~10 KB (ratio ~ 1000:1, exceeding standard safety limit)
        z.writestr("word/document.xml", b"\x00" * (10 * 1024 * 1024))

    bomb_bytes = buf.getvalue()
    with pytest.raises(DecompressionBombDetectedError):
        validate_file_upload("contract_bomb.docx", bomb_bytes)


# =========================================================================
# SEC-011: Zero Raw PII in Metadata and Detection Logs
# =========================================================================
def test_sec_011_zero_raw_pii_in_metadata_logs():
    """PII detection records must store entity offsets and types only, not raw sensitive text."""
    sensitive_text = "Emirates ID is 784-1990-1234567-1 and email is ceo@mizan.ae"
    findings = [
        {
            "id": "f1",
            "start_offset": 15,
            "end_offset": 33,
            "entity_type": "UAE_EMIRATES_ID",
            "detection_score": 0.99,
            "status": FindingStatus.DETECTED,
        },
        {
            "id": "f2",
            "start_offset": 47,
            "end_offset": 59,
            "entity_type": "EMAIL_ADDRESS",
            "detection_score": 0.95,
            "status": FindingStatus.DETECTED,
        },
    ]

    masked_text, count, digest = mask_text(
        canonical_text=sensitive_text,
        findings=findings,
        strategy=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL,
    )

    assert count == 2
    assert "784-1990-1234567-1" not in masked_text
    assert "ceo@mizan.ae" not in masked_text
    assert masked_text == "Emirates ID is [UAE_EMIRATES_ID] and email is [EMAIL_ADDRESS]"
    # Verify findings structure contains zero plaintext PII
    for f in findings:
        assert "784-1990" not in str(f)
        assert "ceo@mizan.ae" not in str(f)


# =========================================================================
# SEC-012: Gate 1 Dataset Substitution Detection
# =========================================================================
def test_sec_012_gate1_dataset_substitution_detected():
    """Gate 1 signature verification must fail if dataset content is substituted."""
    canonical_payload = {
        "schema_version": "gate1-2026-11-09",
        "signature_purpose": "GATE1_DATA_PROTECTION",
        "dataset_version_id": "ds-v-100",
        "content_sha256": "original_dataset_sha256_hash_1234567890abcdef",
    }
    canonical_json, sig_hex, key_id = sign_payload(canonical_payload)

    # Valid check passes
    assert verify_signature(canonical_json, sig_hex, key_id) is True

    # Substituted content payload must fail verification
    tampered_payload = dict(canonical_payload)
    tampered_payload["content_sha256"] = "substituted_malicious_dataset_sha256"
    tampered_json = json.dumps(tampered_payload, sort_keys=True, separators=(",", ":"))

    with pytest.raises(SignatureVerificationError):
        verify_signature(tampered_json, sig_hex, key_id)


# =========================================================================
# SEC-013: Gate 2 Proposal Parameter Tampering Detection
# =========================================================================
def test_sec_013_gate2_proposal_tampering_detected():
    """Gate 2 signature verification must fail if hardware or budget parameters are tampered."""
    proposal_payload = {
        "schema_version": "gate2-2026-11-09",
        "signature_purpose": "GATE2_HARDWARE_RECOMMENDATION",
        "proposal_id": "prop-200",
        "gpu_profile": "NVIDIA_L4_24GB",
        "approved_monthly_budget_usd": 450.0,
    }
    proposal_json, sig_hex, key_id = sign_payload(proposal_payload)

    assert verify_signature(proposal_json, sig_hex, key_id) is True

    # Tampered budget must fail signature verification
    tampered_proposal = dict(proposal_payload)
    tampered_proposal["approved_monthly_budget_usd"] = 9999.0
    tampered_json = json.dumps(tampered_proposal, sort_keys=True, separators=(",", ":"))

    with pytest.raises(SignatureVerificationError):
        verify_signature(tampered_json, sig_hex, key_id)


# =========================================================================
# SEC-014: Gate 3 Release Manifest Tampering Detection
# =========================================================================
def test_sec_014_gate3_manifest_tampering_detected():
    """Gate 3 manifest integrity check must fail if any manifest field is altered."""
    manifest = {
        "manifest_version": "1.0.0",
        "model_family_slug": "compliance-asst",
        "version_tag": "v1.0.0",
        "source_model_key": "mizan/test-llama",
        "source_model_revision": "rev-12345",
        "recipe_key": "LORA_RECIPE_1",
        "artifacts": [
            {
                "artifact_type": "GGUF",
                "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "size_bytes": 1048576,
            }
        ],
    }
    canonical_json, sig_hex, key_id = sign_payload(manifest)

    # Valid manifest signature passes
    assert verify_signature(canonical_json, sig_hex, key_id) is True

    # Tampering with artifact sha256 causes verification to fail
    tampered_manifest = json.loads(canonical_json)
    tampered_manifest["artifacts"][0]["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    tampered_json = json.dumps(tampered_manifest, sort_keys=True, separators=(",", ":"))

    with pytest.raises(SignatureVerificationError):
        verify_signature(tampered_json, sig_hex, key_id)


# =========================================================================
# SEC-015: Signature Purpose Substitution (Cross-Gate Reuse)
# =========================================================================
def test_sec_015_signature_purpose_substitution_rejected():
    """Gate 1 signature must not be accepted as valid for Gate 3."""
    gate1_payload = {
        "approval_id": "appr-123",
        "schema_version": "gate1-2026-11-09",
        "signature_purpose": "GATE1_DATA_PROTECTION",
    }
    gate1_json = json.dumps(gate1_payload, sort_keys=True)

    with pytest.raises(SignaturePurposeMismatchError):
        verify_gate3_attestation(
            canonical_payload_json=gate1_json,
            signature_hex="dummy_sig_hex",
            key_id="mizan-platform-dev-01",
        )


# =========================================================================
# SEC-016: Separation of Duties (Creator Self-Approval Rejected)
# =========================================================================
def test_sec_016_separation_of_duties_enforced(sec_core_env):
    """A model creator cannot approve their own release in Gate 3."""
    engine = sec_core_env["engine"]
    ws_a = sec_core_env["ws_a"]
    org_a = sec_core_env["org_a"]
    user_a = sec_core_env["user_a"]

    with Session(engine) as db:
        # Create model family and version created by user_a
        family = ModelFamily(
            id=f"fam-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            organization_id=org_a.id,
            name="Compliance Assistant",
            slug=f"comp-asst-{uuid.uuid4().hex[:4]}",
            created_by=user_a.id,
        )
        db.add(family)
        db.flush()

        version = ModelVersion(
            id=f"ver-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            organization_id=org_a.id,
            family_id=family.id,
            version_tag="v1.0.0",
            source_model_key="mizan/llama",
            source_model_revision="rev-1",
            recipe_key="REC_1",
            status=ModelVersionStatus.PENDING_REVIEW,
            release_manifest_digest="dummy_manifest_digest_sha256",
            created_by=user_a.id,
        )
        db.add(version)
        db.commit()

        # user_a attempts to approve their own version -> SeparationOfDutiesViolationError
        with pytest.raises(SeparationOfDutiesViolationError):
            submit_gate3_decision(
                db=db,
                workspace_id=ws_a.id,
                model_version_id=version.id,
                reviewer_user=user_a,
                reviewer_role=WorkspaceRole.WORKSPACE_OWNER,
                decision=Gate3Decision.APPROVED,
                enforce_separation_of_duties=True,
            )


# =========================================================================
# SEC-017: Revoked Release Package Installation Rejected
# =========================================================================
def test_sec_017_revoked_release_package_installation_rejected(sec_core_env):
    """Customer Runtime and Site Agent must reject installation of a revoked release."""
    engine = sec_core_env["engine"]
    ws_a = sec_core_env["ws_a"]
    org_a = sec_core_env["org_a"]
    user_a = sec_core_env["user_a"]

    with Session(engine) as db:
        family = ModelFamily(
            id=f"fam-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            organization_id=org_a.id,
            name="Revoked Model Family",
            slug=f"revoked-{uuid.uuid4().hex[:4]}",
            created_by=user_a.id,
        )
        db.add(family)
        db.flush()

        revoked_version = ModelVersion(
            id=f"ver-revoked-{uuid.uuid4().hex[:6]}",
            workspace_id=ws_a.id,
            organization_id=org_a.id,
            family_id=family.id,
            version_tag="v1.0.0",
            source_model_key="mizan/llama",
            source_model_revision="rev-1",
            recipe_key="REC_1",
            status=ModelVersionStatus.REVOKED,
            created_by=user_a.id,
        )
        db.add(revoked_version)
        db.commit()

        # Attempt to install revoked model version via package installer
        from app.models.catalog import AppDefinition, AppVersion
        from app.modules.runtime.exceptions import PackageNotApprovedError
        from app.modules.runtime.package_installer_service import verify_and_install_package

        app_def = AppDefinition(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            app_key=f"support-assistant-{uuid.uuid4().hex[:6]}",
            name="Support Assistant",
            description="Support Assistant Application",
            owner_id=user_a.id,
        )
        db.add(app_def)
        db.flush()

        app_ver = AppVersion(
            app_definition_id=app_def.id,
            version_tag="v1.0.0",
            app_manifest_json='{"entrypoint": "main.py"}',
            manifest_digest="2222222222222222222222222222222222222222222222222222222222222222",
            min_ram_mb=4096.0,
            license_id="Apache-2.0",
            status="ACTIVE",
            created_by=user_a.id,
        )
        db.add(app_ver)

        site = CustomerSite(
            id=f"site-{uuid.uuid4().hex[:6]}",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            site_key=f"edge-{uuid.uuid4().hex[:4]}",
            site_name="Production Edge Site",
            status=SiteStatus.ACTIVE,
            created_by=user_a.id,
        )
        db.add(site)
        db.commit()

        with pytest.raises(PackageNotApprovedError, match="not APPROVED"):
            verify_and_install_package(
                db=db,
                customer_site_id=site.id,
                app_version_id=app_ver.id,
                model_version_id=revoked_version.id,
            )


# =========================================================================
# SEC-018: Unsafe Model Artifact Magic Bytes Rejected
# =========================================================================
def test_sec_018_unsafe_model_artifact_magic_bytes_rejected():
    """Executables (PE/ELF) and untrusted raw scripts must be rejected by file validator."""
    elf_magic = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    pe_magic = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"

    with pytest.raises(FileFormatUnsupportedError):
        validate_file_upload("exploit.exe", pe_magic)

    with pytest.raises(FileFormatUnsupportedError):
        validate_file_upload("backdoor.elf", elf_magic)


# =========================================================================
# SEC-019: Cross-Tenant RAG Retrieval Strictly Filtered
# =========================================================================
def test_sec_019_cross_tenant_rag_retrieval_isolated():
    """RAG vector store retrieval queries must strictly isolate results by workspace_id."""
    from app.modules.rag.vector_store.base import VectorRecord
    from app.modules.rag.vector_store.qdrant_local import QdrantLocalVectorStore

    store = QdrantLocalVectorStore(in_memory=True)
    collection = "security_rag_tenant_test"
    store.create_collection(collection_name=collection, dimension=4)

    ws_a_id = "ws-tenant-alpha-001"
    ws_b_id = "ws-tenant-beta-002"

    records_ws1 = [
        VectorRecord(
            id="00000000-0000-0000-0000-000000000001",
            vector=[0.1, 0.2, 0.3, 0.4],
            payload={
                "workspace_id": ws_a_id,
                "dataset_version_id": "ver-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Alpha highly confidential executive memo",
            },
        ),
    ]
    records_ws2 = [
        VectorRecord(
            id="00000000-0000-0000-0000-000000000002",
            vector=[0.1, 0.2, 0.3, 0.4],
            payload={
                "workspace_id": ws_b_id,
                "dataset_version_id": "ver-1",
                "document_id": "doc-2",
                "chunk_index": 0,
                "text": "Beta general announcement",
            },
        ),
    ]

    store.upsert_chunks(collection, records_ws1)
    store.upsert_chunks(collection, records_ws2)

    # 1. Tenant B searches with identical vector -> must NEVER get Alpha memo
    results_b = store.search_chunks(
        collection_name=collection,
        query_vector=[0.1, 0.2, 0.3, 0.4],
        workspace_id=ws_b_id,
        top_k=5,
    )
    assert len(results_b) == 1
    assert "Alpha" not in results_b[0].text
    assert results_b[0].payload["workspace_id"] == ws_b_id

    # 2. Tenant A searches -> gets only Alpha memo
    results_a = store.search_chunks(
        collection_name=collection,
        query_vector=[0.1, 0.2, 0.3, 0.4],
        workspace_id=ws_a_id,
        top_k=5,
    )
    assert len(results_a) == 1
    assert "Alpha" in results_a[0].text
    assert results_a[0].payload["workspace_id"] == ws_a_id


# =========================================================================
# SEC-020: Invalid Site Agent Command Signature Rejected
# =========================================================================
def test_sec_020_invalid_site_agent_command_signature_rejected():
    """Site Agent command execution must reject commands with invalid Ed25519 signatures."""
    command_payload = {
        "command_id": "cmd-555",
        "site_id": "site-alpha",
        "command_type": "STAGE_SLOT",
        "nonce": uuid.uuid4().hex,
        "issued_at": datetime.now(UTC).isoformat(),
    }
    canonical_json, sig_hex, key_id = sign_payload(command_payload)

    bad_signature_hex = "00" * 64
    with pytest.raises(SignatureVerificationError):
        verify_signature(canonical_json, bad_signature_hex, key_id)
