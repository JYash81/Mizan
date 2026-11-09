import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import get_db
from app.models.identity import AccountStatus, AuthSession, User
from app.modules.audit.services.audit_service import (
    list_audit_events,
    record_audit_event,
    sanitize_metadata,
)
from app.modules.auth.dependencies import (
    get_current_active_user,
    get_optional_principal,
    require_csrf,
)
from app.modules.auth.services.session_service import IssuedSession, create_session


def _create_test_app(engine):
    app = FastAPI()
    register_exception_handlers(app)

    def _override_get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    @app.get("/test/public")
    def public_route(principal=Depends(get_optional_principal)):
        return {
            "authenticated": principal is not None,
            "user_id": principal.user_id if principal else None,
        }

    @app.get("/test/protected")
    def protected_route(user=Depends(get_current_active_user)):
        return {"user_id": user.id, "email": user.email}

    @app.post("/test/csrf-guarded", dependencies=[Depends(require_csrf)])
    def csrf_guarded_route(user=Depends(get_current_active_user)):
        return {"status": "success", "user_id": user.id}

    return app


@pytest.fixture
def test_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    active_user = User(
        full_name="Active Alice",
        email="alice@example.com",
        normalized_email="alice@example.com",
        password_hash="argon2id$mocked",
        status=AccountStatus.ACTIVE,
    )
    suspended_user = User(
        full_name="Suspended Sam",
        email="sam@example.com",
        normalized_email="sam@example.com",
        password_hash="argon2id$mocked",
        status=AccountStatus.SUSPENDED,
    )
    db.add_all([active_user, suspended_user])
    db.commit()

    app = _create_test_app(engine)
    client = TestClient(app)
    return engine, db, active_user, suspended_user, client


# --- Audit Service Tests ---


def test_sanitize_metadata_strips_secrets() -> None:
    raw = {
        "action": "user_login",
        "password": "plain_password",
        "api_token": "secret_token",
        "session_cookie": "secret_cookie",
        "nested": {
            "safe_field": 123,
            "user_credential": "bad",
            "deep": [{"inner_secret": "bad2", "keep": "ok"}],
        },
    }
    clean = sanitize_metadata(raw)
    assert "password" not in clean
    assert "api_token" not in clean
    assert "session_cookie" not in clean
    assert clean["nested"]["safe_field"] == 123
    assert "user_credential" not in clean["nested"]
    assert clean["nested"]["deep"][0] == {"keep": "ok"}


def test_record_audit_event_and_list(test_setup) -> None:
    _, db, user, _, _ = test_setup
    meta = {"action": "profile_update", "ip": "127.0.0.1", "password_leak": "omit_me"}

    event = record_audit_event(
        db=db,
        event_type="USER_PROFILE_UPDATED",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        correlation_id="corr-123",
        safe_metadata=meta,
    )
    db.commit()

    assert event.id is not None
    assert event.safe_metadata is not None
    assert "password_leak" not in event.safe_metadata
    assert event.safe_metadata["action"] == "profile_update"

    # List audit events
    results = list_audit_events(db, actor_user_id=user.id)
    assert len(results) >= 1
    assert results[0].event_type == "USER_PROFILE_UPDATED"
    assert results[0].correlation_id == "corr-123"


# --- Authentication Dependency Tests ---


def test_public_route_without_and_with_auth(test_setup) -> None:
    _, db, user, _, client = test_setup

    # Unauthenticated
    res = client.get("/test/public")
    assert res.status_code == 200
    assert res.json() == {"authenticated": False, "user_id": None}

    # Authenticated via cookie
    issued: IssuedSession = create_session(db, user.id)
    db.commit()

    res = client.get("/test/public", cookies={"mizan_session": issued.session_token})
    assert res.status_code == 200
    assert res.json() == {"authenticated": True, "user_id": user.id}


def test_protected_route_rejection_and_success(test_setup) -> None:
    _, db, user, suspended_user, client = test_setup

    # 401 when no session provided
    res = client.get("/test/protected")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"

    # 401 with invalid session token
    res = client.get("/test/protected", cookies={"mizan_session": "invalid-token"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"

    # 200 with valid cookie session
    issued = create_session(db, user.id)
    db.commit()
    res = client.get("/test/protected", cookies={"mizan_session": issued.session_token})
    assert res.status_code == 200
    assert res.json()["user_id"] == user.id

    # 200 with Bearer authorization header
    res = client.get(
        "/test/protected",
        headers={"Authorization": f"Bearer {issued.session_token}"},
    )
    assert res.status_code == 200
    assert res.json()["user_id"] == user.id

    # 403 when user is suspended
    # Note: create_session rejects non-active users, so simulate a session that existed before suspension
    issued_sam = create_session(db, user.id)
    db.commit()
    # Reassign session to suspended user directly for test
    sess_record = db.get(AuthSession, issued_sam.session_id)
    sess_record.user_id = suspended_user.id
    db.commit()

    res = client.get("/test/protected", cookies={"mizan_session": issued_sam.session_token})
    assert res.status_code == 401  # validate_session rejects non-active users at session level


def test_csrf_guard_enforcement(test_setup) -> None:
    _, db, user, _, client = test_setup
    issued: IssuedSession = create_session(db, user.id)
    db.commit()

    cookie = {"mizan_session": issued.session_token}

    # 1. State-changing POST with cookie but MISSING CSRF header -> 403 FORBIDDEN
    res = client.post("/test/csrf-guarded", cookies=cookie)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. POST with WRONG CSRF header -> 403 FORBIDDEN
    res = client.post(
        "/test/csrf-guarded",
        cookies=cookie,
        headers={"X-CSRF-Token": "bogus-csrf-token"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 3. POST with VALID CSRF header -> 200 OK
    res = client.post(
        "/test/csrf-guarded",
        cookies=cookie,
        headers={"X-CSRF-Token": issued.csrf_token},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 4. Programmatic API with Bearer token (no cookie) -> succeeds without CSRF header
    res = client.post(
        "/test/csrf-guarded",
        headers={"Authorization": f"Bearer {issued.session_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
