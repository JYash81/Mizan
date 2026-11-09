import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service
from app.modules.email.provider import get_email_provider


@pytest.fixture
def auth_client():
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
    return client, engine


def test_registration_and_email_verification_flow(auth_client):
    client, engine = auth_client
    email_prov = get_email_provider()

    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Bob Builder",
            "email": "bob@builder.com",
            "password": "ValidPassword123!",
            "password_confirm": "ValidPassword123!",
            "terms_accepted": True,
        },
    )
    assert reg_res.status_code == 201
    assert "Registration successful" in reg_res.json()["data"]["message"]

    # Verify email was dispatched to development sink
    email = email_prov.get_latest_for("bob@builder.com")
    assert email is not None
    token = email.context["token"]

    # 2. Login before verification must be rejected
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@builder.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 403
    assert "verify your email" in login_res.json()["error"]["message"]

    # 3. Verify email with invalid token fails
    verify_bad = client.post("/api/v1/auth/verify-email", json={"token": "bogus-token"})
    assert verify_bad.status_code == 400

    # 4. Verify email with valid token succeeds
    verify_ok = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_ok.status_code == 200
    assert "Email verified successfully" in verify_ok.json()["data"]["message"]

    # Replay of token fails
    verify_replay = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_replay.status_code == 400

    # 5. Login after verification succeeds
    login_ok = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@builder.com", "password": "ValidPassword123!"},
    )
    assert login_ok.status_code == 200
    assert "mizan_session" in login_ok.cookies
    assert login_ok.json()["data"]["user"]["email"] == "bob@builder.com"
    assert login_ok.json()["data"]["csrf_token"] is not None

    # 6. Call /me endpoint with session cookie
    me_res = client.get(
        "/api/v1/auth/me",
        cookies={"mizan_session": login_ok.cookies["mizan_session"]},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["user"]["full_name"] == "Bob Builder"

    # 7. Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        cookies={"mizan_session": login_ok.cookies["mizan_session"]},
    )
    assert logout_res.status_code == 200

    # /me after logout fails
    me_after = client.get(
        "/api/v1/auth/me",
        cookies={"mizan_session": login_ok.cookies["mizan_session"]},
    )
    assert me_after.status_code == 401


def test_repeat_registration_resends_verification_for_pending_account(auth_client):
    """A pending account receives a fresh link when the user safely retries registration."""
    client, _ = auth_client
    email_prov = get_email_provider()

    payload = {
        "full_name": "Pending User",
        "email": "pending@example.com",
        "password": "ValidPassword123!",
        "password_confirm": "ValidPassword123!",
        "terms_accepted": True,
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    first_email = email_prov.get_latest_for("pending@example.com")
    assert first_email is not None

    retry = client.post("/api/v1/auth/register", json=payload)
    # The endpoint keeps its generic 201 response for both first-time and
    # retry submissions so account existence is not exposed.
    assert retry.status_code == 201
    assert "verification link has been sent" in retry.json()["data"]["message"]

    resent_email = email_prov.get_latest_for("pending@example.com")
    assert resent_email is not None
    assert resent_email.context["token"] != first_email.context["token"]


def test_password_reset_flow(auth_client):
    client, engine = auth_client
    email_prov = get_email_provider()

    # Pre-seed verified active user
    db = Session(engine)
    user = User(
        full_name="Reset User",
        email="reset@test.com",
        normalized_email="reset@test.com",
        password_hash=password_service.hash_password("OldPassword123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.commit()

    # 1. Forgot password
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": "reset@test.com"})
    assert forgot_res.status_code == 200

    email = email_prov.get_latest_for("reset@test.com")
    assert email is not None
    token = email.context["token"]

    # 2. Reset password
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewSecretPassword123!",
            "new_password_confirm": "NewSecretPassword123!",
        },
    )
    assert reset_res.status_code == 200

    # 3. Old password fails
    login_old = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@test.com", "password": "OldPassword123!"},
    )
    assert login_old.status_code == 401

    # 4. New password succeeds
    login_new = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@test.com", "password": "NewSecretPassword123!"},
    )
    assert login_new.status_code == 200
