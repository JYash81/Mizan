"""Audit service for tamper-evident, privacy-preserving operational audit logging.

Enforces strict metadata sanitation so credentials and secrets never persist in audit logs.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import AuditEvent

FORBIDDEN_TERMS = ("password", "token", "session", "cookie", "secret", "credential")


def sanitize_metadata(data: Any) -> Any:
    """Recursively scrub any key containing credential or secret terms."""
    if isinstance(data, Mapping):
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key).lower()
            if any(term in key_str for term in FORBIDDEN_TERMS):
                continue
            cleaned[str(key)] = sanitize_metadata(value)
        return cleaned
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        return [sanitize_metadata(item) for item in data]
    return data


def record_audit_event(
    db: Session,
    event_type: str,
    resource_type: str,
    resource_id: str | None = None,
    actor_user_id: str | None = None,
    correlation_id: str | None = None,
    safe_metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Create and persist an append-only audit record with sanitized metadata."""
    cleaned_meta = sanitize_metadata(safe_metadata) if safe_metadata else None
    now = datetime.now(UTC)

    event = AuditEvent(
        actor_user_id=actor_user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        safe_metadata=cleaned_meta,
        created_at=now,
    )
    db.add(event)
    db.flush()
    return event


def list_audit_events(
    db: Session,
    actor_user_id: str | None = None,
    event_type: str | None = None,
    resource_type: str | None = None,
    correlation_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditEvent]:
    """Retrieve audit events with optional filtering, ordered newest first."""
    stmt = select(AuditEvent)
    if actor_user_id is not None:
        stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
    if event_type is not None:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if resource_type is not None:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    if correlation_id is not None:
        stmt = stmt.where(AuditEvent.correlation_id == correlation_id)

    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
