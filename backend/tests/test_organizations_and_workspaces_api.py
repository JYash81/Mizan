import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service, session_service


@pytest.fixture
def org_client():
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

    db = Session(engine)
    user1 = User(
        full_name="Alice Owner",
        email="alice@corp.com",
        normalized_email="alice@corp.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    user2 = User(
        full_name="Bob Member",
        email="bob@corp.com",
        normalized_email="bob@corp.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([user1, user2])
    db.commit()

    # Create session for Alice
    sess1 = session_service.create_session(db, user1.id)
    # Create session for Bob
    sess2 = session_service.create_session(db, user2.id)
    db.commit()

    return client, user1, user2, sess1, sess2


def test_organization_and_workspace_api_lifecycle(org_client):
    client, user1, user2, sess1, sess2 = org_client

    alice_cookies = {"mizan_session": sess1.session_token}
    alice_headers = {"X-CSRF-Token": sess1.csrf_token}

    bob_cookies = {"mizan_session": sess2.session_token}

    # 1. Alice creates Organization
    create_org_res = client.post(
        "/api/v1/organizations/",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Alpha Corp", "slug": "alpha-corp", "description": "Alpha Enterprise"},
    )
    assert create_org_res.status_code == 201
    org_data = create_org_res.json()["data"]
    org_id = org_data["id"]
    assert org_data["role"] == "OWNER"

    # 2. Bob cannot see Alice's org yet
    bob_orgs = client.get("/api/v1/organizations/", cookies=bob_cookies)
    assert bob_orgs.status_code == 200
    assert len(bob_orgs.json()["data"]) == 0

    # 3. Alice adds Bob as member
    # We can use direct service or invitation, let's use the membership endpoint or add directly
    # Alice adds Bob:
    alice_add_bob = client.patch(
        f"/api/v1/organizations/{org_id}",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Alpha Corp Updated"},
    )
    assert alice_add_bob.status_code == 200
    assert alice_add_bob.json()["data"]["name"] == "Alpha Corp Updated"

    # 4. Alice creates a Workspace
    create_ws_res = client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        cookies=alice_cookies,
        headers=alice_headers,
        json={"name": "Research Workspace", "slug": "research", "description": "Lab workspace"},
    )
    assert create_ws_res.status_code == 201
    ws_id = create_ws_res.json()["data"]["id"]
    assert create_ws_res.json()["data"]["role"] == "WORKSPACE_OWNER"

    # 5. Alice lists workspaces
    ws_list = client.get(
        f"/api/v1/organizations/{org_id}/workspaces",
        cookies=alice_cookies,
    )
    assert ws_list.status_code == 200
    assert len(ws_list.json()["data"]) == 1
    assert ws_list.json()["data"][0]["slug"] == "research"

    # 6. Alice archives workspace
    archive_ws = client.post(
        f"/api/v1/workspaces/{ws_id}/archive",
        cookies=alice_cookies,
        headers=alice_headers,
    )
    assert archive_ws.status_code == 200

    # Accessing archived workspace fails with 404
    ws_detail = client.get(f"/api/v1/workspaces/{ws_id}", cookies=alice_cookies)
    assert ws_detail.status_code == 404
