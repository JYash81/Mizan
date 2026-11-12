"""Incident Regulatory Clocks & Timed Escalation Service.

Implements Section 10 of Mizan Security Strategy v2:
- Tracks GDPR 72-hour breach notification clock from time of awareness.
- Tracks contractual customer-notification SLA clocks.
- Drives automatic multi-tier escalation when alerts/incidents remain unacknowledged.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import Incident, IncidentStatus
from app.models.sentinel import IncidentRegulatoryClock
from app.modules.sentinel.schemas import IncidentRegulatoryClockRead


def get_incident_regulatory_clock(
    db: Session,
    incident_id: str,
) -> IncidentRegulatoryClockRead | None:
    """Retrieves and calculates remaining time for regulatory clocks."""
    clock = db.execute(
        select(IncidentRegulatoryClock).where(IncidentRegulatoryClock.incident_id == incident_id)
    ).scalar_one_or_none()

    if not clock:
        return None

    now = datetime.now(UTC)
    gdpr_dl = clock.gdpr_deadline
    if gdpr_dl.tzinfo is None:
        gdpr_dl = gdpr_dl.replace(tzinfo=UTC)

    contract_dl = clock.customer_contract_deadline
    if contract_dl.tzinfo is None:
        contract_dl = contract_dl.replace(tzinfo=UTC)

    gdpr_remaining = (gdpr_dl - now).total_seconds() / 3600.0
    contract_remaining = (contract_dl - now).total_seconds() / 3600.0

    return IncidentRegulatoryClockRead(
        id=clock.id,
        incident_id=clock.incident_id,
        workspace_id=clock.workspace_id,
        awareness_at=clock.awareness_at,
        gdpr_deadline=clock.gdpr_deadline,
        customer_contract_deadline=clock.customer_contract_deadline,
        gdpr_notified_at=clock.gdpr_notified_at,
        customer_notified_at=clock.customer_notified_at,
        escalation_level=clock.escalation_level,
        last_escalated_at=clock.last_escalated_at,
        gdpr_hours_remaining=round(gdpr_remaining, 2),
        contract_hours_remaining=round(contract_remaining, 2),
        is_gdpr_breached=now > gdpr_dl and clock.gdpr_notified_at is None,
        is_contract_breached=now > contract_dl and clock.customer_notified_at is None,
        created_at=clock.created_at,
    )


def check_and_escalate_unacknowledged_incidents(
    db: Session,
    workspace_id: str,
    escalation_timeout_minutes: int = 15,
) -> list[dict[str, Any]]:
    """Checks for open/unacknowledged incidents and escalates them along the escalation chain."""
    now = datetime.now(UTC)

    clocks = (
        db.execute(
            select(IncidentRegulatoryClock)
            .join(Incident, IncidentRegulatoryClock.incident_id == Incident.id)
            .where(IncidentRegulatoryClock.workspace_id == workspace_id)
            .where(Incident.status == IncidentStatus.OPEN)
        )
        .scalars()
        .all()
    )

    escalations = []
    for clock in clocks:
        awareness = clock.awareness_at
        if awareness.tzinfo is None:
            awareness = awareness.replace(tzinfo=UTC)

        # Check if overdue for escalation
        last_escalation = clock.last_escalated_at or awareness
        if last_escalation.tzinfo is None:
            last_escalation = last_escalation.replace(tzinfo=UTC)

        if now - last_escalation >= timedelta(minutes=escalation_timeout_minutes):
            clock.escalation_level += 1
            clock.last_escalated_at = now

            target_role = "Primary On-Call"
            if clock.escalation_level == 1:
                target_role = "Backup Responder"
            elif clock.escalation_level == 2:
                target_role = "Security Lead / Incident Commander"
            else:
                target_role = "Executive / CISO Contact"

            escalations.append(
                {
                    "incident_id": clock.incident_id,
                    "escalated_to_level": clock.escalation_level,
                    "target_role": target_role,
                    "escalated_at": now.isoformat(),
                }
            )

    db.commit()
    return escalations
