"""Security regression tests for Operations Metrics Endpoints.

Verifies authentication, authorization, token comparison, fail-closed production semantics,
tenant isolation, and data-protection checks across:
- GET /api/v1/ops/metrics/summary
- GET /api/v1/ops/metrics
- GET /api/v1/ops/metrics/prometheus
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.models.organization import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.modules.auth.services import password_service, session_service


@pytest.fixture
def test_db_and_client(monkeypatch):
    """Provides an isolated SQLite in-memory test database and client."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Configure a known scrape token for testing
    settings = get_settings()
    monkeypatch.setattr(settings, "prometheus_scrape_token", "test-scrape-token-valid-entropy-32chars")
    monkeypatch.setattr(settings, "platform_operator_emails", ["platform-operator@mizan.ai"])

    with Session(engine) as db:
        # Create users
        hashed = password_service.hash_password("StrongPassword123!@#")

        # 1. Platform Operator
        op_user = User(
            id=str(uuid.uuid4()),
            email="platform-operator@mizan.ai",
            normalized_email="platform-operator@mizan.ai",
            full_name="Platform Operator",
            password_hash=hashed,
            status=AccountStatus.ACTIVE,
        )
        db.add(op_user)

        # 2. Org Owner (Workspace A)
        owner_user = User(
            id=str(uuid.uuid4()),
            email="owner@org-a.com",
            normalized_email="owner@org-a.com",
            full_name="Org Owner A",
            password_hash=hashed,
            status=AccountStatus.ACTIVE,
        )
        db.add(owner_user)

        # 3. Workspace Member (Workspace A)
        member_user = User(
            id=str(uuid.uuid4()),
            email="member@org-a.com",
            normalized_email="member@org-a.com",
            full_name="Workspace Member A",
            password_hash=hashed,
            status=AccountStatus.ACTIVE,
        )
        db.add(member_user)

        # 4. Workspace Member (Workspace B)
        other_user = User(
            id=str(uuid.uuid4()),
            email="member@org-b.com",
            normalized_email="member@org-b.com",
            full_name="Workspace Member B",
            password_hash=hashed,
            status=AccountStatus.ACTIVE,
        )
        db.add(other_user)

        # Organizations & Workspaces
        org_a = Organization(id=str(uuid.uuid4()), name="Org A", slug="org-a", created_by=owner_user.id)
        org_b = Organization(id=str(uuid.uuid4()), name="Org B", slug="org-b", created_by=other_user.id)
        db.add_all([org_a, org_b])

        ws_a = Workspace(id=str(uuid.uuid4()), organization_id=org_a.id, name="WS A", slug="ws-a", created_by=owner_user.id)
        ws_b = Workspace(id=str(uuid.uuid4()), organization_id=org_b.id, name="WS B", slug="ws-b", created_by=other_user.id)
        db.add_all([ws_a, ws_b])

        # Memberships
        db.add(OrganizationMembership(organization_id=org_a.id, user_id=owner_user.id, role=OrganizationRole.OWNER, membership_status=MembershipStatus.ACTIVE))
        db.add(OrganizationMembership(organization_id=org_a.id, user_id=member_user.id, role=OrganizationRole.MEMBER, membership_status=MembershipStatus.ACTIVE))
        db.add(OrganizationMembership(organization_id=org_b.id, user_id=other_user.id, role=OrganizationRole.OWNER, membership_status=MembershipStatus.ACTIVE))

        db.add(WorkspaceMembership(workspace_id=ws_a.id, user_id=owner_user.id, role=WorkspaceRole.WORKSPACE_OWNER))
        db.add(WorkspaceMembership(workspace_id=ws_a.id, user_id=member_user.id, role=WorkspaceRole.WORKSPACE_MEMBER))
        db.add(WorkspaceMembership(workspace_id=ws_b.id, user_id=other_user.id, role=WorkspaceRole.WORKSPACE_OWNER))

        db.commit()

        # Generate sessions
        op_tok = session_service.create_session(db, op_user.id)
        owner_tok = session_service.create_session(db, owner_user.id)
        member_tok = session_service.create_session(db, member_user.id)
        other_tok = session_service.create_session(db, other_user.id)
        db.commit()

        meta = {
            "ws_a_id": ws_a.id,
            "ws_b_id": ws_b.id,
            "op_headers": {"Authorization": f"Bearer {op_tok.session_token}"},
            "owner_headers": {"Authorization": f"Bearer {owner_tok.session_token}"},
            "member_headers": {"Authorization": f"Bearer {member_tok.session_token}"},
            "other_headers": {"Authorization": f"Bearer {other_tok.session_token}"},
            "scrape_token": "test-scrape-token-valid-entropy-32chars",
        }

    client = TestClient(app)
    return client, meta


def test_anonymous_metrics_summary_rejected(test_db_and_client):
    """Anonymous metrics summary request must return 401 Unauthorized."""
    client, meta = test_db_and_client
    res = client.get("/api/v1/ops/metrics/summary")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


def test_anonymous_raw_metrics_rejected(test_db_and_client):
    """Anonymous raw metrics request must return 401 Unauthorized."""
    client, meta = test_db_and_client
    res = client.get("/api/v1/ops/metrics")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


def test_anonymous_prometheus_rejected(test_db_and_client):
    """Anonymous Prometheus scrape request must return 401 Unauthorized."""
    client, meta = test_db_and_client
    res = client.get("/api/v1/ops/metrics/prometheus")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


def test_incorrect_prometheus_scrape_token_rejected(test_db_and_client):
    """Prometheus scrape with invalid token must return 401 Unauthorized."""
    client, meta = test_db_and_client
    res = client.get(
        "/api/v1/ops/metrics/prometheus",
        headers={"Authorization": "Bearer wrong-token-xyz"},
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


def test_missing_production_scrape_token_fails_closed(test_db_and_client, monkeypatch):
    """If scrape token is unconfigured in production, endpoint must fail closed with 503."""
    client, meta = test_db_and_client
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "prometheus_scrape_token", None)

    res = client.get(
        "/api/v1/ops/metrics/prometheus",
        headers={"Authorization": "Bearer any-token"},
    )
    assert res.status_code == 503, f"Expected 503 fail-closed, got {res.status_code}: {res.text}"


def test_valid_prometheus_scrape_token_accepted(test_db_and_client):
    """Valid scrape token returns 200 OK and formatted Prometheus text."""
    client, meta = test_db_and_client
    res = client.get(
        "/api/v1/ops/metrics/prometheus",
        headers={"Authorization": f"Bearer {meta['scrape_token']}"},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert "text/plain" in res.headers.get("content-type", "")


def test_authenticated_user_without_operations_permission_rejected(test_db_and_client):
    """Ordinary workspace member requesting global metrics without workspace_id is rejected with 403."""
    client, meta = test_db_and_client
    res = client.get("/api/v1/ops/metrics/summary", headers=meta["member_headers"])
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


def test_authorized_operations_administrator_accepted(test_db_and_client):
    """Platform operator can retrieve global metrics summary."""
    client, meta = test_db_and_client
    res = client.get("/api/v1/ops/metrics/summary", headers=meta["op_headers"])
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert "active_slot" in res.json()


def test_workspace_scoped_metrics_summary_accepted(test_db_and_client):
    """Workspace member can retrieve metrics summary for their own workspace."""
    client, meta = test_db_and_client
    res = client.get(
        f"/api/v1/ops/metrics/summary?workspace_id={meta['ws_a_id']}",
        headers=meta["member_headers"],
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"


def test_cross_workspace_metrics_access_rejected(test_db_and_client):
    """User from Workspace B cannot access metrics for Workspace A (anti-enumeration 404)."""
    client, meta = test_db_and_client
    res = client.get(
        f"/api/v1/ops/metrics/summary?workspace_id={meta['ws_a_id']}",
        headers=meta["other_headers"],
    )
    # Anti-enumeration returns 404 for workspaces user does not belong to
    assert res.status_code in [403, 404], f"Expected 403/404, got {res.status_code}: {res.text}"


def test_metrics_output_contains_no_prompts_pii_or_secrets(test_db_and_client):
    """Metrics outputs must not disclose internal secrets, passwords, or PII."""
    client, meta = test_db_and_client
    res_prom = client.get(
        "/api/v1/ops/metrics/prometheus",
        headers={"Authorization": f"Bearer {meta['scrape_token']}"},
    )
    assert res_prom.status_code == 200
    text_prom = res_prom.text.lower()
    assert "password" not in text_prom
    assert "secret" not in text_prom
    assert "token" not in text_prom

    res_sum = client.get(
        f"/api/v1/ops/metrics/summary?workspace_id={meta['ws_a_id']}",
        headers=meta["member_headers"],
    )
    assert res_sum.status_code == 200
    text_sum = res_sum.text.lower()
    assert "password" not in text_sum
    assert "secret" not in text_sum
