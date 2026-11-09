"""Sanitized, append-only operational event journal service."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.observability import OperationalEvent
from app.modules.observability.schemas import OperationalEventCreate, OperationalEventRead
from app.modules.observability.telemetry_privacy import sanitize_event_payload


def record_operational_event(
    db: Session,
    payload: OperationalEventCreate,
) -> OperationalEventRead:
    """Record an operational lifecycle event with strict payload sanitization."""
    clean_payload = sanitize_event_payload(payload.payload)

    event = OperationalEvent(
        customer_site_id=payload.customer_site_id,
        workspace_id=payload.workspace_id,
        event_type=payload.event_type,
        severity=payload.severity,
        source_component=payload.source_component,
        summary=payload.summary[:255],
        payload_json=json.dumps(clean_payload),
        created_at=datetime.now(UTC),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return _to_event_read(event)


def list_operational_events(
    db: Session,
    workspace_id: str | None = None,
    customer_site_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 50,
) -> list[OperationalEventRead]:
    """Retrieve chronologically ordered operational events matching filters."""
    query = select(OperationalEvent).order_by(desc(OperationalEvent.created_at))

    if workspace_id:
        query = query.where(OperationalEvent.workspace_id == workspace_id)
    if customer_site_id:
        query = query.where(OperationalEvent.customer_site_id == customer_site_id)
    if event_type:
        query = query.where(OperationalEvent.event_type == event_type)
    if severity:
        query = query.where(OperationalEvent.severity == severity)

    events = db.execute(query.limit(limit)).scalars().all()
    return [_to_event_read(e) for e in events]


def _to_event_read(e: OperationalEvent) -> OperationalEventRead:
    return OperationalEventRead(
        id=e.id,
        customer_site_id=e.customer_site_id,
        workspace_id=e.workspace_id,
        event_type=e.event_type,
        severity=e.severity,
        source_component=e.source_component,
        summary=e.summary,
        payload=e.payload,
        created_at=e.created_at,
    )
