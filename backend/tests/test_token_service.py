import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.models.identity import AccountStatus, AuthToken, TokenPurpose, User
from app.modules.auth.services.token_service import (
    cleanup_expired_tokens,
    consume_token,
    create_token,
    revoke_token,
    revoke_user_tokens,
    validate_token,
)


def _setup_db() -> tuple[Session, User]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        full_name="Token Test User",
        email="token@example.com",
        normalized_email="token@example.com",
        password_hash="argon2id$mocked",
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    return db, user


def test_token_creation_and_hashing() -> None:
    db, user = _setup_db()
    issued = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    # Raw token must not appear in string representation
    assert issued.raw_token not in repr(issued)

    stored = db.get(AuthToken, issued.token_id)
    assert stored is not None
    assert stored.token_hash != issued.raw_token
    assert stored.token_hash == hashlib.sha256(issued.raw_token.encode("utf-8")).hexdigest()
    assert stored.purpose == TokenPurpose.EMAIL_VERIFICATION
    assert stored.user_id == user.id
    assert stored.consumed_at is None
    assert stored.revoked_at is None


def test_token_lifespan_defaults_and_override() -> None:
    db, user = _setup_db()
    settings = Settings(email_verification_token_hours=48, password_reset_token_minutes=30)

    # Email verification default
    email_tok = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION, settings=settings)
    assert email_tok.expires_at > datetime.now(UTC) + timedelta(hours=47)

    # Password reset default
    reset_tok = create_token(db, user.id, TokenPurpose.PASSWORD_RESET, settings=settings)
    assert reset_tok.expires_at > datetime.now(UTC) + timedelta(minutes=28)
    assert reset_tok.expires_at < datetime.now(UTC) + timedelta(minutes=32)

    # Custom override
    custom_tok = create_token(
        db, user.id, TokenPurpose.PASSWORD_RESET, expires_in_minutes=10, settings=settings
    )
    assert custom_tok.expires_at < datetime.now(UTC) + timedelta(minutes=11)


def test_validate_token_success_and_failures() -> None:
    db, user = _setup_db()
    issued = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    # Valid validation
    record = validate_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION)
    assert record is not None
    assert record.id == issued.token_id

    # Invalid raw token string
    assert validate_token(db, "wrong-token", TokenPurpose.EMAIL_VERIFICATION) is None
    assert validate_token(db, "", TokenPurpose.EMAIL_VERIFICATION) is None

    # Purpose mismatch must reject
    assert validate_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET) is None


def test_atomic_single_use_consumption() -> None:
    db, user = _setup_db()
    issued = create_token(db, user.id, TokenPurpose.PASSWORD_RESET)
    db.commit()

    # First consumption succeeds
    consumed = consume_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET)
    db.commit()
    assert consumed is not None
    assert consumed.consumed_at is not None

    # Second consumption of the same token MUST fail (single-use guarantee)
    second_attempt = consume_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET)
    assert second_attempt is None

    # Validating a consumed token must return None
    assert validate_token(db, issued.raw_token, TokenPurpose.PASSWORD_RESET) is None


def test_expired_token_cannot_be_validated_or_consumed() -> None:
    db, user = _setup_db()
    issued = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    # Force expiration into past
    record = db.get(AuthToken, issued.token_id)
    record.expires_at = datetime.now(UTC) - timedelta(seconds=10)
    db.commit()

    assert validate_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION) is None
    assert consume_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION) is None


def test_revoked_token_cannot_be_validated_or_consumed() -> None:
    db, user = _setup_db()
    issued = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    assert revoke_token(db, issued.token_id) is True
    db.commit()

    assert validate_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION) is None
    assert consume_token(db, issued.raw_token, TokenPurpose.EMAIL_VERIFICATION) is None


def test_superseded_tokens_are_revoked_on_new_issue() -> None:
    db, user = _setup_db()
    first = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    # Creating a second token for the same purpose supersedes the first
    second = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    assert validate_token(db, first.raw_token, TokenPurpose.EMAIL_VERIFICATION) is None
    assert validate_token(db, second.raw_token, TokenPurpose.EMAIL_VERIFICATION) is not None


def test_revoke_user_tokens() -> None:
    db, user = _setup_db()
    t1 = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    t2 = create_token(db, user.id, TokenPurpose.PASSWORD_RESET)
    db.commit()

    # Revoke only password reset tokens
    assert revoke_user_tokens(db, user.id, purpose=TokenPurpose.PASSWORD_RESET) == 1
    db.commit()

    assert validate_token(db, t1.raw_token, TokenPurpose.EMAIL_VERIFICATION) is not None
    assert validate_token(db, t2.raw_token, TokenPurpose.PASSWORD_RESET) is None


def test_nonexistent_user_rejected() -> None:
    db, _ = _setup_db()
    with pytest.raises(ValueError, match="User not found"):
        create_token(db, "nonexistent-user-id", TokenPurpose.EMAIL_VERIFICATION)


def test_cleanup_expired_tokens() -> None:
    db, user = _setup_db()
    settings = Settings(token_retention_days=15)
    t = create_token(db, user.id, TokenPurpose.EMAIL_VERIFICATION)
    db.commit()

    # Expired 20 days ago (older than retention 15 days)
    old_record = db.get(AuthToken, t.token_id)
    old_record.expires_at = datetime.now(UTC) - timedelta(days=20)
    db.commit()

    deleted = cleanup_expired_tokens(db, settings=settings)
    db.commit()
    assert deleted == 1
    assert db.get(AuthToken, t.token_id) is None
