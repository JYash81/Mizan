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
from app.modules.email.provider import get_email_provider
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def inv_fixture():
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
    get_email_provider().clear()

    db = Session(engine, expire_on_commit=False)
    owner = User(
        full_name="Owner Oscar",
        email="oscar@org.com",
        normalized_email="oscar@org.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    charlie = User(
        full_name="Charlie Candidate",
        email="charlie@invited.com",
        normalized_email="charlie@invited.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    impostor = User(
        full_name="Impostor Ian",
        email="ian@attacker.com",
        normalized_email="ian@attacker.com",
        password_hash=password_service.hash_password("Password123456!"),
        status=AccountStatus.ACTIVE,
    )
    db.add_all([owner, charlie, impostor])
    db.commit()

    org, _ = organization_service.create_organization(
        db, owner.id, "Omega Enterprises", "omega-enterprises"
    )
    ws, _ = workspace_service.create_workspace(
        db, org.id, owner.id, "Omega Production", "omega-prod"
    )
    db.commit()

    org_id = org.id
    ws_id = ws.id

    s_owner = session_service.create_session(db, owner.id)
    s_charlie = session_service.create_session(db, charlie.id)
    s_impostor = session_service.create_session(db, impostor.id)
    db.commit()

    return client, org_id, ws_id, s_owner, s_charlie, s_impostor


def test_invitation_lifecycle_and_security(inv_fixture):
    client, org_id, ws_id, s_owner, s_charlie, s_impostor = inv_fixture
    email_prov = get_email_provider()

    owner_cookies = {"mizan_session": s_owner.session_token}
    owner_headers = {"X-CSRF-Token": s_owner.csrf_token}

    charlie_cookies = {"mizan_session": s_charlie.session_token}
    charlie_headers = {"X-CSRF-Token": s_charlie.csrf_token}

    impostor_cookies = {"mizan_session": s_impostor.session_token}
    impostor_headers = {"X-CSRF-Token": s_impostor.csrf_token}

    # 1. Owner invites Charlie
    create_res = client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        cookies=owner_cookies,
        headers=owner_headers,
        json={
            "email": "charlie@invited.com",
            "organization_role": "MEMBER",
            "workspace_id": ws_id,
            "workspace_role": "WORKSPACE_MEMBER",
        },
    )
    assert create_res.status_code == 201

    # Extract token from development email outbox
    email = email_prov.get_latest_for("charlie@invited.com")
    assert email is not None
    token = email.context["token"]

    # 2. Impostor tries to accept Charlie's invitation -> Must be REJECTED (400)
    impostor_accept = client.post(
        "/api/v1/invitations/accept",
        cookies=impostor_cookies,
        headers=impostor_headers,
        json={"token": token},
    )
    assert impostor_accept.status_code == 400
    assert "email does not match" in impostor_accept.json()["error"]["message"]

    # 3. Charlie accepts his invitation -> SUCCEEDS (200)
    charlie_accept = client.post(
        "/api/v1/invitations/accept",
        cookies=charlie_cookies,
        headers=charlie_headers,
        json={"token": token},
    )
    assert charlie_accept.status_code == 200
    assert charlie_accept.json()["data"]["organization_id"] == org_id

    # 4. Charlie can now view the organization and workspace
    charlie_orgs = client.get("/api/v1/organizations/", cookies=charlie_cookies)
    assert charlie_orgs.status_code == 200
    assert len(charlie_orgs.json()["data"]) == 1

    charlie_ws = client.get(f"/api/v1/workspaces/{ws_id}", cookies=charlie_cookies)
    assert charlie_ws.status_code == 200

    # 5. Replay fails
    charlie_replay = client.post(
        "/api/v1/invitations/accept",
        cookies=charlie_cookies,
        headers=charlie_headers,
        json={"token": token},
    )
    assert charlie_replay.status_code == 400
