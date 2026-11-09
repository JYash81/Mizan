"""Secure one-time token lifecycle service.

Raw tokens are cryptographically random, never logged, and never persisted directly.
Only a SHA-256 digest is stored in the database.
Consumption is strictly atomic and single-use.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.identity import AuthToken, TokenPurpose, User


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IssuedToken:
    token_id: str
    user_id: str
    purpose: TokenPurpose
    raw_token: str = field(repr=False)
    expires_at: datetime


def create_token(
    db: Session,
    user_id: str,
    purpose: TokenPurpose,
    expires_in_minutes: int | None = None,
    settings: Settings | None = None,
) -> IssuedToken:
    """Issue a high-entropy one-time token for email verification or password reset.

    Existing active tokens for this user and purpose are automatically revoked before
    issuing the replacement. The raw token is returned only once and must be transmitted
    to the user via an out-of-band channel (e.g. email).
    """
    settings = settings or get_settings()
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")

    # Revoke any prior unconsumed, unrevoked tokens for this purpose
    revoke_user_tokens(db, user_id=user.id, purpose=purpose, reason="superseded")

    now = datetime.now(UTC)
    if expires_in_minutes is not None:
        lifespan = timedelta(minutes=expires_in_minutes)
    elif purpose == TokenPurpose.EMAIL_VERIFICATION:
        lifespan = timedelta(hours=settings.email_verification_token_hours)
    elif purpose == TokenPurpose.PASSWORD_RESET:
        lifespan = timedelta(minutes=settings.password_reset_token_minutes)
    else:
        lifespan = timedelta(minutes=15)

    raw_token = secrets.token_urlsafe(32)
    record = AuthToken(
        user_id=user.id,
        token_hash=_digest(raw_token),
        purpose=purpose,
        created_at=now,
        expires_at=now + lifespan,
    )
    db.add(record)
    db.flush()
    return IssuedToken(
        token_id=record.id,
        user_id=user.id,
        purpose=purpose,
        raw_token=raw_token,
        expires_at=record.expires_at,
    )


def validate_token(
    db: Session,
    raw_token: str,
    purpose: TokenPurpose,
) -> AuthToken | None:
    """Inspect and validate a token without consuming it.

    Returns the AuthToken record if valid, unconsumed, unrevoked, and unexpired;
    otherwise returns None.
    """
    if not isinstance(raw_token, str) or not raw_token:
        return None

    digest = _digest(raw_token)
    record = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == digest,
            AuthToken.purpose == purpose,
            AuthToken.consumed_at.is_(None),
            AuthToken.revoked_at.is_(None),
        )
    )
    if record is None:
        return None

    now = datetime.now(UTC)
    if _utc(record.expires_at) <= now:
        return None

    return record


def consume_token(
    db: Session,
    raw_token: str,
    purpose: TokenPurpose,
) -> AuthToken | None:
    """Atomically consume a one-time token.

    Guarantees single-use semantics via conditional UPDATE. If the token is already
    consumed, revoked, expired, or has a mismatched purpose, returns None.
    """
    record = validate_token(db, raw_token, purpose)
    if record is None:
        return None

    now = datetime.now(UTC)

    # Atomic conditional update: only one concurrent consumer can transition consumed_at
    stmt = (
        update(AuthToken)
        .where(
            AuthToken.id == record.id,
            AuthToken.consumed_at.is_(None),
            AuthToken.revoked_at.is_(None),
        )
        .values(consumed_at=now)
        .execution_options(synchronize_session="fetch")
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        return None

    db.flush()
    return db.get(AuthToken, record.id)


def revoke_token(db: Session, token_id: str) -> bool:
    """Revoke a specific token by its ID."""
    now = datetime.now(UTC)
    result = db.execute(
        update(AuthToken)
        .where(AuthToken.id == token_id, AuthToken.revoked_at.is_(None))
        .values(revoked_at=now)
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount == 1


def revoke_user_tokens(
    db: Session,
    user_id: str,
    purpose: TokenPurpose | None = None,
    reason: str = "revoked",
) -> int:
    """Revoke all active tokens for a user, optionally filtered by purpose."""
    now = datetime.now(UTC)
    conditions = [
        AuthToken.user_id == user_id,
        AuthToken.revoked_at.is_(None),
        AuthToken.consumed_at.is_(None),
    ]
    if purpose is not None:
        conditions.append(AuthToken.purpose == purpose)

    result = db.execute(
        update(AuthToken)
        .where(*conditions)
        .values(revoked_at=now)
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount or 0


def cleanup_expired_tokens(db: Session, settings: Settings | None = None) -> int:
    """Purge token records older than the configured retention cutoff."""
    settings = settings or get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.token_retention_days)
    result = db.execute(
        delete(AuthToken)
        .where(AuthToken.expires_at < cutoff)
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount or 0
