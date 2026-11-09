"""Tenant isolation and anti-enumeration tests for Masking and Gate 1."""

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
from app.modules.auth.services import password_service, session_service
from app.modules.datasets.services import dataset_service
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
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

    # Tenant 1: Alpha
    user_alpha = User(
        full_name="Alpha Owner",
        email="owner@alpha.ae",
        normalized_email="owner@alpha.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    # Tenant 2: Beta
    user_beta = User(
        full_name="Beta Owner",
        email="owner@beta.ae",
        normalized_email="owner@beta.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([user_alpha, user_beta])
    db.commit()

    alpha_sess = session_service.create_session(db, user_alpha.id)
    beta_sess = session_service.create_session(db, user_beta.id)
    db.commit()

    org_a, _ = organization_service.create_organization(db, user_alpha.id, "Alpha Org", "alpha-org")
    ws_a, _ = workspace_service.create_workspace(
        db, org_a.id, user_alpha.id, "Alpha WS", "alpha-ws"
    )

    org_b, _ = organization_service.create_organization(db, user_beta.id, "Beta Org", "beta-org")
    ws_b, _ = workspace_service.create_workspace(db, org_b.id, user_beta.id, "Beta WS", "beta-ws")

    yield {
        "client": client,
        "engine": engine,
        "ws_a_id": ws_a.id,
        "ws_b_id": ws_b.id,
        "alpha_cookies": {"mizan_session": alpha_sess.session_token},
        "alpha_headers": {"X-CSRF-Token": alpha_sess.csrf_token},
        "beta_cookies": {"mizan_session": beta_sess.session_token},
        "beta_headers": {"X-CSRF-Token": beta_sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_cross_tenant_masking_isolation(multi_tenant_env):
    client = multi_tenant_env["client"]
    ws_a_id = multi_tenant_env["ws_a_id"]
    ws_b_id = multi_tenant_env["ws_b_id"]
    alpha_cookies = multi_tenant_env["alpha_cookies"]
    alpha_headers = multi_tenant_env["alpha_headers"]
    beta_cookies = multi_tenant_env["beta_cookies"]
    beta_headers = multi_tenant_env["beta_headers"]
    engine = multi_tenant_env["engine"]

    db = Session(engine, expire_on_commit=False)

    # Alpha creates dataset and run in Workspace A
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws_a_id}/datasets",
        json={"name": "Alpha Data", "slug": "alpha-data"},
        cookies=alpha_cookies,
        headers=alpha_headers,
    )
    dataset_id = ds_resp.json()["dataset"]["id"]
    version_id = ds_resp.json()["version"]["id"]

    ver = db.query(dataset_service.DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "alphahash"
    db.commit()

    run_resp = client.post(
        f"/api/v1/workspaces/{ws_a_id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        cookies=alpha_cookies,
        headers=alpha_headers,
    )
    run_id = run_resp.json()["id"]

    # Beta attempts to read Alpha's masking run in Workspace A -> 404 (Anti-enumeration)
    res_a = client.get(
        f"/api/v1/workspaces/{ws_a_id}/masking-runs/{run_id}",
        cookies=beta_cookies,
    )
    assert res_a.status_code == 404

    # Beta attempts to access Alpha's run via Workspace B route -> 404
    res_b = client.get(
        f"/api/v1/workspaces/{ws_b_id}/masking-runs/{run_id}",
        cookies=beta_cookies,
    )
    assert res_b.status_code == 404

    # Beta attempts to approve Alpha's run -> 404
    res_approve = client.post(
        f"/api/v1/workspaces/{ws_b_id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "Malicious cross-tenant attempt"},
        cookies=beta_cookies,
        headers=beta_headers,
    )
    assert res_approve.status_code == 404
