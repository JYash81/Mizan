"""Tenant isolation and anti-enumeration security tests for Datasets and Documents."""

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.models.organization import OrganizationRole, WorkspaceRole
from app.modules.auth.services import password_service, session_service
from app.modules.datasets.services import dataset_service
from app.modules.documents.services import document_service
from app.modules.storage import LocalStorageProvider, set_storage_provider_override
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def multi_tenant_env():
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

    # 1. User Alice in Org A, Workspace A
    alice = User(
        full_name="Alice Alpha",
        email="alice@alpha.com",
        normalized_email="alice@alpha.com",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    # 2. User Bob in Org B, Workspace B
    bob = User(
        full_name="Bob Beta",
        email="bob@beta.com",
        normalized_email="bob@beta.com",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    # 3. User Charlie (Viewer in Workspace A)
    charlie = User(
        full_name="Charlie Viewer",
        email="charlie@alpha.com",
        normalized_email="charlie@alpha.com",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([alice, bob, charlie])
    db.commit()

    sess_alice = session_service.create_session(db, alice.id)
    sess_bob = session_service.create_session(db, bob.id)
    sess_charlie = session_service.create_session(db, charlie.id)
    db.commit()

    # Create Org Alpha and Workspace Alpha
    org_a, _ = organization_service.create_organization(db, alice.id, "Alpha Org", "alpha-org")
    ws_a, _ = workspace_service.create_workspace(db, org_a.id, alice.id, "Alpha WS", "alpha-ws")

    # Add Charlie as VIEWER in Org A and Workspace A
    organization_service.add_organization_member(
        db, org_a.id, charlie.id, role=OrganizationRole.MEMBER
    )
    workspace_service.add_workspace_member(
        db, ws_a.id, charlie.id, role=WorkspaceRole.WORKSPACE_VIEWER, actor_id=alice.id
    )

    # Create Org Beta and Workspace Beta
    org_b, _ = organization_service.create_organization(db, bob.id, "Beta Org", "beta-org")
    ws_b, _ = workspace_service.create_workspace(db, org_b.id, bob.id, "Beta WS", "beta-ws")

    # Create a Dataset and Document in Beta WS (belonging to Bob)
    ds_b, ver_b = dataset_service.create_dataset(
        db, ws_b.id, bob.id, "Beta Secret Data", "Secret", slug="beta-secret"
    )
    doc_b, _ = document_service.upload_document(
        db, storage, ws_b.id, ver_b.id, "secret.txt", b"Confidential Beta IP", actor_id=bob.id
    )

    yield {
        "client": client,
        "alice_cookies": {"mizan_session": sess_alice.session_token},
        "alice_headers": {"X-CSRF-Token": sess_alice.csrf_token},
        "bob_cookies": {"mizan_session": sess_bob.session_token},
        "bob_headers": {"X-CSRF-Token": sess_bob.csrf_token},
        "charlie_cookies": {"mizan_session": sess_charlie.session_token},
        "charlie_headers": {"X-CSRF-Token": sess_charlie.csrf_token},
        "ws_a_id": ws_a.id,
        "ws_b_id": ws_b.id,
        "ds_b_id": ds_b.id,
        "ver_b_id": ver_b.id,
        "doc_b_id": doc_b.id,
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_cross_tenant_dataset_access_returns_404(multi_tenant_env):
    """Alice must not be able to list, view, update or delete Bob's datasets (returns 404 anti-enumeration)."""
    client = multi_tenant_env["client"]
    alice_cookies = multi_tenant_env["alice_cookies"]
    alice_headers = multi_tenant_env["alice_headers"]
    ws_b_id = multi_tenant_env["ws_b_id"]
    ds_b_id = multi_tenant_env["ds_b_id"]

    # 1. Alice attempts to list datasets in Bob's workspace
    res = client.get(
        f"/api/v1/workspaces/{ws_b_id}/datasets",
        cookies=alice_cookies,
    )
    assert res.status_code == 404

    # 2. Alice attempts to get Bob's dataset
    res = client.get(
        f"/api/v1/workspaces/{ws_b_id}/datasets/{ds_b_id}",
        cookies=alice_cookies,
    )
    assert res.status_code == 404

    # 3. Alice attempts to update Bob's dataset
    res = client.patch(
        f"/api/v1/workspaces/{ws_b_id}/datasets/{ds_b_id}",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Hacked Name"},
    )
    assert res.status_code == 404

    # 4. Alice attempts to delete Bob's dataset
    res = client.delete(
        f"/api/v1/workspaces/{ws_b_id}/datasets/{ds_b_id}",
        cookies=alice_cookies,
        headers=alice_headers,
    )
    assert res.status_code == 404


def test_cross_tenant_document_access_returns_404(multi_tenant_env):
    """Alice must not be able to upload or access Bob's documents."""
    client = multi_tenant_env["client"]
    alice_cookies = multi_tenant_env["alice_cookies"]
    alice_headers = multi_tenant_env["alice_headers"]
    ws_b_id = multi_tenant_env["ws_b_id"]
    ds_b_id = multi_tenant_env["ds_b_id"]
    ver_b_id = multi_tenant_env["ver_b_id"]
    doc_b_id = multi_tenant_env["doc_b_id"]

    # 1. Alice attempts to upload document to Bob's dataset version
    res = client.post(
        f"/api/v1/workspaces/{ws_b_id}/datasets/{ds_b_id}/versions/{ver_b_id}/documents/upload",
        cookies=alice_cookies,
        headers=alice_headers,
        files={"file": ("infiltrate.txt", b"malicious", "text/plain")},
    )
    assert res.status_code == 404

    # 2. Alice attempts to read Bob's document
    res = client.get(
        f"/api/v1/workspaces/{ws_b_id}/documents/{doc_b_id}",
        cookies=alice_cookies,
    )
    assert res.status_code == 404

    # 3. Alice attempts to delete Bob's document
    res = client.delete(
        f"/api/v1/workspaces/{ws_b_id}/documents/{doc_b_id}",
        cookies=alice_cookies,
        headers=alice_headers,
    )
    assert res.status_code == 404


def test_workspace_viewer_role_permissions(multi_tenant_env):
    """Charlie (Viewer in WS A) can read datasets, but is forbidden (403) from modifying or uploading."""
    client = multi_tenant_env["client"]
    charlie_cookies = multi_tenant_env["charlie_cookies"]
    charlie_headers = multi_tenant_env["charlie_headers"]
    ws_a_id = multi_tenant_env["ws_a_id"]

    # 1. Charlie lists datasets in WS A -> 200 OK (empty list)
    res = client.get(
        f"/api/v1/workspaces/{ws_a_id}/datasets",
        cookies=charlie_cookies,
    )
    assert res.status_code == 200

    # 2. Charlie attempts to create a dataset -> 403 Forbidden
    res = client.post(
        f"/api/v1/workspaces/{ws_a_id}/datasets",
        cookies=charlie_cookies,
        headers=charlie_headers,
        json={"name": "Viewer Dataset", "slug": "viewer-ds"},
    )
    assert res.status_code == 403
    assert "Permission denied" in res.json()["error"]["message"]
