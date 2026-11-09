from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.identity import AccountStatus, AuthSession, User
from app.modules.auth.services import session_service
from app.modules.auth.services.session_service import (
    create_session,
    revoke_all_user_sessions,
    rotate_session,
    validate_csrf,
    validate_session,
)


def database() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(
        User(
            full_name="Active",
            email="a@test",
            normalized_email="a@test",
            password_hash="x",
            status=AccountStatus.ACTIVE,
        )
    )
    db.commit()
    return db


def test_session_hashing_validation_rotation_and_csrf() -> None:
    db = database()
    user = db.query(User).one()
    issued = create_session(db, user.id)
    db.commit()
    stored = db.get(AuthSession, issued.session_id)
    assert (
        issued.session_token not in repr(issued)
        and stored.session_token_hash != issued.session_token
    )
    assert validate_session(db, issued.session_token) is not None
    assert validate_csrf(db, issued.session_token, issued.csrf_token)
    rotated = rotate_session(db, issued.session_token)
    db.commit()
    assert rotated is not None and validate_session(db, issued.session_token) is None
    assert validate_session(db, rotated.session_token) is not None


def test_expiration_and_user_wide_revocation() -> None:
    db = database()
    user = db.query(User).one()
    first = create_session(db, user.id)
    second = create_session(db, user.id)
    db.commit()
    assert revoke_all_user_sessions(db, user.id) == 2
    db.commit()
    assert (
        validate_session(db, first.session_token) is None
        and validate_session(db, second.session_token) is None
    )


def test_expired_session_fails() -> None:
    db = database()
    user = db.query(User).one()
    issued = create_session(db, user.id)
    db.get(AuthSession, issued.session_id).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert validate_session(db, issued.session_token) is None


def test_failed_rotation_rolls_back_old_session(monkeypatch) -> None:
    db = database()
    issued = create_session(db, db.query(User).one().id)
    db.commit()

    def fail_create(*args, **kwargs):
        raise RuntimeError("insertion failure")

    monkeypatch.setattr(session_service, "create_session", fail_create)
    with pytest.raises(RuntimeError):
        session_service.rotate_session(db, issued.session_token)
    assert validate_session(db, issued.session_token) is not None
