import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.models.organization import Organization, OrganizationStatus
from app.modules.auth.services import password_service, session_service
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def multi_tenant_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    db = Session(engine, expire_on_commit=False)

    # Tenant A
    user_a = User(
        full_name="Alice TenantA",
        email="alice@tenanta.com",
        normalized_email="alice@tenanta.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    # Tenant B
    user_b = User(
        full_name="Bob TenantB",
        email="bob@tenantb.com",
        normalized_email="bob@tenantb.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([user_a, user_b])
    db.commit()

    org_a, _ = organization_service.create_organization(db, user_a.id, "Tenant A Org", "tenant-a")
    ws_a, _ = workspace_service.create_workspace(db, org_a.id, user_a.id, "Workspace A", "ws-a")

    org_b, _ = organization_service.create_organization(db, user_b.id, "Tenant B Org", "tenant-b")
    ws_b, _ = workspace_service.create_workspace(db, org_b.id, user_b.id, "Workspace B", "ws-b")

    db.commit()

    org_a_id = org_a.id
    ws_a_id = ws_a.id
    org_b_id = org_b.id
    ws_b_id = ws_b.id

    sess_a = session_service.create_session(db, user_a.id)
    sess_b = session_service.create_session(db, user_b.id)
    db.commit()

    return client, org_a_id, ws_a_id, sess_a, org_b_id, ws_b_id, sess_b, engine


def test_cross_tenant_isolation_enforcement(multi_tenant_fixture):
    client, org_a_id, ws_a_id, sess_a, org_b_id, ws_b_id, sess_b, engine = multi_tenant_fixture

    alice_cookies = {"mizan_session": sess_a.session_token}
    alice_headers = {"X-CSRF-Token": sess_a.csrf_token}

    bob_cookies = {"mizan_session": sess_b.session_token}

    # 1. Alice cannot read Org B details (404 Not Found to prevent enumeration)
    res1 = client.get(f"/api/v1/organizations/{org_b_id}", cookies=alice_cookies)
    assert res1.status_code == 404

    # 2. Alice cannot list Org B workspaces
    res2 = client.get(f"/api/v1/organizations/{org_b_id}/workspaces", cookies=alice_cookies)
    assert res2.status_code == 404

    # 3. Alice cannot access Workspace B directly
    res3 = client.get(f"/api/v1/workspaces/{ws_b_id}", cookies=alice_cookies)
    assert res3.status_code == 404

    # 4. Alice cannot list Org B members
    res4 = client.get(f"/api/v1/organizations/{org_b_id}/members", cookies=alice_cookies)
    assert res4.status_code == 404

    # 5. Alice cannot update Org B
    res5 = client.patch(
        f"/api/v1/organizations/{org_b_id}",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Hacked Org"},
    )
    assert res5.status_code == 404

    # 6. Alice cannot create a workspace inside Org B
    res6 = client.post(
        f"/api/v1/organizations/{org_b_id}/workspaces",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Illegal Workspace", "slug": "illegal"},
    )
    assert res6.status_code == 404

    # 7. Bob cannot access Org A or Workspace A
    assert client.get(f"/api/v1/organizations/{org_a_id}", cookies=bob_cookies).status_code == 404
    assert client.get(f"/api/v1/workspaces/{ws_a_id}", cookies=bob_cookies).status_code == 404

    # 8. Suspended organization returns 403
    db = Session(engine)
    db_org = db.get(Organization, org_a_id)
    assert db_org is not None
    db_org.status = OrganizationStatus.SUSPENDED
    db.commit()

    suspended_res = client.get(f"/api/v1/organizations/{org_a_id}", cookies=alice_cookies)
    assert suspended_res.status_code == 403
    assert "suspended" in suspended_res.json()["error"]["message"]
