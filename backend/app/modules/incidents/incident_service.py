"""Incident creation, lifecycle transitions, and chronological event logging."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.observability import (
    Incident,
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
)
from app.modules.incidents.schemas import (
    IncidentCreate,
    IncidentEventRead,
    IncidentRead,
    IncidentUpdate,
)


def create_incident(
    db: Session,
    workspace_id: str,
    payload: IncidentCreate,
    actor_id: str,
) -> IncidentRead:
    """Create an operational incident and record the initial opening event."""
    # Find next incident number for this workspace
    max_num = db.execute(
        select(func.max(Incident.incident_number)).where(Incident.workspace_id == workspace_id)
    ).scalar_one_or_none()
    next_num = (max_num or 0) + 1

    now = datetime.now(UTC)
    incident = Incident(
        workspace_id=workspace_id,
        customer_site_id=payload.customer_site_id,
        runtime_application_id=payload.runtime_application_id,
        incident_number=next_num,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        status=IncidentStatus.OPEN,
        primary_alert_id=payload.primary_alert_id,
        assigned_to=payload.assigned_to,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(incident)
    db.flush()

    # Append initial creation event
    initial_event = IncidentEvent(
        incident_id=incident.id,
        event_type="STATUS_CHANGE",
        description=f"Incident opened with severity {payload.severity.value}",
        actor_id=actor_id,
        created_at=now,
    )
    db.add(initial_event)
    db.commit()
    db.refresh(incident)

    return _to_incident_read(incident)


def list_incidents(
    db: Session,
    workspace_id: str,
    status: IncidentStatus | None = None,
    severity: IncidentSeverity | None = None,
    customer_site_id: str | None = None,
    limit: int = 50,
) -> list[IncidentRead]:
    """Retrieve chronologically ordered incidents for a workspace."""
    query = (
        select(Incident)
        .where(Incident.workspace_id == workspace_id)
        .order_by(desc(Incident.created_at))
    )

    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
    if customer_site_id:
        query = query.where(Incident.customer_site_id == customer_site_id)

    incidents = db.execute(query.limit(limit)).scalars().all()
    return [_to_incident_read(inc) for inc in incidents]


def get_incident_detail(
    db: Session,
    incident_id: str,
) -> IncidentRead | None:
    """Retrieve incident details including its full timeline."""
    incident = db.execute(select(Incident).where(Incident.id == incident_id)).scalar_one_or_none()
    if not incident:
        return None
    return _to_incident_read(incident)


def update_incident(
    db: Session,
    incident_id: str,
    payload: IncidentUpdate,
    actor_id: str,
) -> IncidentRead:
    """Update incident status, severity, assignment, and record timeline audit."""
    incident = db.execute(select(Incident).where(Incident.id == incident_id)).scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident '{incident_id}' not found.")

    now = datetime.now(UTC)

    if payload.title is not None:
        incident.title = payload.title
    if payload.description is not None:
        incident.description = payload.description
    if payload.assigned_to is not None:
        incident.assigned_to = payload.assigned_to

    if payload.severity is not None and payload.severity != incident.severity:
        old_sev = incident.severity.value
        incident.severity = payload.severity
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="SEVERITY_CHANGE",
                description=f"Severity changed from {old_sev} to {payload.severity.value}",
                actor_id=actor_id,
                created_at=now,
            )
        )

    if payload.status is not None and payload.status != incident.status:
        old_status = incident.status.value
        incident.status = payload.status
        note_str = f" - Note: {payload.status_change_note}" if payload.status_change_note else ""
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="STATUS_CHANGE",
                description=f"Status transitioned from {old_status} to {payload.status.value}{note_str}",
                actor_id=actor_id,
                created_at=now,
            )
        )

        if payload.status == IncidentStatus.RESOLVED:
            incident.resolved_at = now
        elif payload.status == IncidentStatus.CLOSED:
            incident.closed_at = now

    incident.updated_at = now
    db.commit()
    db.refresh(incident)
    return _to_incident_read(incident)


def add_incident_note(
    db: Session,
    incident_id: str,
    note: str,
    actor_id: str,
) -> IncidentEventRead:
    """Add an operator investigation note to the incident timeline."""
    incident = db.execute(select(Incident).where(Incident.id == incident_id)).scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident '{incident_id}' not found.")

    now = datetime.now(UTC)
    event = IncidentEvent(
        incident_id=incident.id,
        event_type="NOTE",
        description=note,
        actor_id=actor_id,
        created_at=now,
    )
    db.add(event)
    incident.updated_at = now
    db.commit()
    db.refresh(event)

    return IncidentEventRead(
        id=event.id,
        incident_id=event.incident_id,
        event_type=event.event_type,
        description=event.description,
        actor_id=event.actor_id,
        created_at=event.created_at,
    )


def _to_incident_read(inc: Incident) -> IncidentRead:
    events = sorted(inc.events, key=lambda e: e.created_at) if inc.events else []
    return IncidentRead(
        id=inc.id,
        workspace_id=inc.workspace_id,
        incident_number=inc.incident_number,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        customer_site_id=inc.customer_site_id,
        runtime_application_id=inc.runtime_application_id,
        primary_alert_id=inc.primary_alert_id,
        assigned_to=inc.assigned_to,
        created_by=inc.created_by,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        resolved_at=inc.resolved_at,
        closed_at=inc.closed_at,
        events=[
            IncidentEventRead(
                id=e.id,
                incident_id=e.incident_id,
                event_type=e.event_type,
                description=e.description,
                actor_id=e.actor_id,
                created_at=e.created_at,
            )
            for e in events
        ],
    )
