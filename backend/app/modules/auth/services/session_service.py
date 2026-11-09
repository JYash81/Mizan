"""Opaque server-side session lifecycle; raw credentials never persist or log."""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.identity import AccountStatus, AuthSession, User


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IssuedSession:
    session_id: str
    csrf_token: str = field(repr=False)
    session_token: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    session_id: str
    account_status: AccountStatus
    session_expires_at: datetime


def create_session(db: Session, user_id: str, settings: Settings | None = None) -> IssuedSession:
    settings = settings or get_settings()
    user = db.get(User, user_id)
    if user is None or user.status is not AccountStatus.ACTIVE:
        raise ValueError("User is not eligible for a session.")
    now = datetime.now(UTC)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    record = AuthSession(
        user_id=user.id,
        session_token_hash=_digest(token),
        csrf_token_hash=_digest(csrf),
        last_activity_at=now,
        expires_at=now + timedelta(minutes=settings.session_absolute_minutes),
    )
    db.add(record)
    db.flush()
    return IssuedSession(record.id, csrf, token, record.expires_at)


def validate_session(
    db: Session, token: str, settings: Settings | None = None
) -> AuthenticatedPrincipal | None:
    settings = settings or get_settings()
    if not isinstance(token, str) or not token:
        return None
    record = db.scalar(select(AuthSession).where(AuthSession.session_token_hash == _digest(token)))
    if record is None or record.revoked_at is not None:
        return None
    now = datetime.now(UTC)
    if (
        _utc(record.expires_at) <= now
        or _utc(record.last_activity_at) + timedelta(minutes=settings.session_idle_minutes) <= now
    ):
        return None
    user = db.get(User, record.user_id)
    if user is None or user.status is not AccountStatus.ACTIVE:
        return None
    if now - _utc(record.last_activity_at) >= timedelta(
        minutes=settings.session_activity_update_minutes
    ):
        record.last_activity_at = now
        db.flush()
    return AuthenticatedPrincipal(user.id, record.id, user.status, _utc(record.expires_at))


def revoke_session(db: Session, session_id: str, reason: str = "revoked") -> bool:
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revocation_reason=reason)
    )
    return result.rowcount == 1


def revoke_all_user_sessions(
    db: Session, user_id: str, reason: str = "user-wide-revocation"
) -> int:
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revocation_reason=reason)
    )
    return result.rowcount or 0


def rotate_session(
    db: Session, token: str, settings: Settings | None = None
) -> IssuedSession | None:
    """Atomically revoke one active credential and issue exactly one replacement.

    The conditional update is the concurrency gate: only the transaction that changes
    ``revoked_at`` from NULL can issue a replacement. The nested transaction restores
    the old session if replacement persistence fails.
    """
    principal = validate_session(db, token, settings)
    if principal is None:
        return None
    try:
        with db.begin_nested():
            if not revoke_session(db, principal.session_id, "rotated"):
                return None
            replacement = create_session(db, principal.user_id, settings)
        # A savepoint is not durable: commit before returning a credential.
        db.commit()
        return replacement
    except Exception:
        db.rollback()
        raise


def validate_csrf(db: Session, token: str, csrf: str, settings: Settings | None = None) -> bool:
    principal = validate_session(db, token, settings)
    if principal is None or not isinstance(csrf, str) or not csrf:
        return False
    record = db.get(AuthSession, principal.session_id)
    return record is not None and secrets.compare_digest(record.csrf_token_hash, _digest(csrf))


def cleanup_expired_sessions(db: Session, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.session_retention_days)
    result = db.execute(delete(AuthSession).where(AuthSession.expires_at < cutoff))
    return result.rowcount or 0
