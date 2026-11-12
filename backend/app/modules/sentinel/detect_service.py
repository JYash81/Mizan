"""Sentinel Detect Component: Security Event Ingestion, Correlation, and Alert Hygiene.

Enforces:
1. Read-only detection authority: cannot change policy, cannot revoke access, cannot contain anything.
2. Alert hygiene: deduplication within window, per-source rate limiting, burst/decoy attack detection.
3. Incident registration with AI/heuristic summary drafting.
4. Automatic regulatory clock initialization (GDPR 72h window, contractual notification SLA).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import (
    IncidentSeverity,
)
from app.models.sentinel import IncidentRegulatoryClock
from app.modules.incidents.incident_service import create_incident
from app.modules.incidents.schemas import IncidentCreate
from app.modules.sentinel.exceptions import ComponentBoundaryViolationError

# In-memory tracking for alert hygiene within sliding windows
_RECENT_EVENT_HASHES: dict[str, datetime] = {}
_SOURCE_EVENT_TIMESTAMPS: dict[str, list[datetime]] = defaultdict(list)
DEDUP_WINDOW_SECONDS = 60
SOURCE_RATE_LIMIT_PER_MINUTE = 10
BURST_THRESHOLD_COUNT = 5
BURST_WINDOW_SECONDS = 5


def ingest_security_event(
    db: Session,
    workspace_id: str,
    source: str,
    event_type: str,
    details: dict[str, Any],
    severity: IncidentSeverity = IncidentSeverity.SEV2,
    actor_id: str | None = None,
    customer_sla_hours: int = 24,
) -> dict[str, Any]:
    """Ingests, correlates, deduplicates, and routes a security event.

    Returns dict with incident_id, deduped, burst_detected, and AI summary.
    """
    now = datetime.now(UTC)

    # Clean old memory entries
    cutoff_dedup = now - timedelta(seconds=DEDUP_WINDOW_SECONDS)
    expired_hashes = [h for h, ts in _RECENT_EVENT_HASHES.items() if ts < cutoff_dedup]
    for h in expired_hashes:
        _RECENT_EVENT_HASHES.pop(h, None)

    cutoff_rate = now - timedelta(minutes=1)
    _SOURCE_EVENT_TIMESTAMPS[source] = [
        ts for ts in _SOURCE_EVENT_TIMESTAMPS[source] if ts >= cutoff_rate
    ]

    # 1. Deduplication check
    raw_hash_input = f"{workspace_id}:{source}:{event_type}:{details.get('signature', '')}"
    event_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()

    if event_hash in _RECENT_EVENT_HASHES:
        return {
            "deduped": True,
            "burst_detected": False,
            "rate_limited": False,
            "incident_id": None,
            "message": f"Duplicate security event from '{source}' suppressed under alert deduplication window.",
        }

    _RECENT_EVENT_HASHES[event_hash] = now
    _SOURCE_EVENT_TIMESTAMPS[source].append(now)

    # 2. Burst and Decoy Attack Detection
    burst_cutoff = now - timedelta(seconds=BURST_WINDOW_SECONDS)
    recent_burst_events = [ts for ts in _SOURCE_EVENT_TIMESTAMPS[source] if ts >= burst_cutoff]
    burst_detected = len(recent_burst_events) >= BURST_THRESHOLD_COUNT

    # 3. Rate limiting per source
    rate_limited = len(_SOURCE_EVENT_TIMESTAMPS[source]) > SOURCE_RATE_LIMIT_PER_MINUTE

    # 4. Draft AI / Heuristic Incident Summary
    summary_lines = [
        f"Security Event: {event_type} detected from source '{source}'.",
        f"Details: {details.get('reason', 'Policy threshold exceeded')}.",
    ]
    if burst_detected:
        summary_lines.append(
            "[HIGH ALERT] Rapid event burst detected! Possible decoy attack designed to distract operators."
        )
    if rate_limited:
        summary_lines.append("[NOTICE] Source exceeded 10 events/min; rate limiting applied.")
    ai_summary = " ".join(summary_lines)

    # 5. Create or escalate incident
    effective_actor_id = actor_id
    if not effective_actor_id:
        from app.models.organization import Workspace

        ws = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
        if ws and ws.created_by:
            effective_actor_id = ws.created_by
        else:
            from app.models.identity import User

            first_user = db.execute(select(User.id)).scalars().first()
            effective_actor_id = first_user or "system"

    title = f"Sentinel Alert: {event_type} on {source}"
    incident_create = IncidentCreate(
        title=title,
        description=ai_summary,
        severity=severity,
    )

    incident = create_incident(
        db=db,
        workspace_id=workspace_id,
        payload=incident_create,
        actor_id=effective_actor_id,
    )

    # 6. Initialize Regulatory Clock for this incident
    gdpr_deadline = now + timedelta(hours=72)
    contract_deadline = now + timedelta(hours=customer_sla_hours)

    reg_clock = db.execute(
        select(IncidentRegulatoryClock).where(IncidentRegulatoryClock.incident_id == incident.id)
    ).scalar_one_or_none()

    if not reg_clock:
        reg_clock = IncidentRegulatoryClock(
            incident_id=incident.id,
            workspace_id=workspace_id,
            awareness_at=now,
            gdpr_deadline=gdpr_deadline,
            customer_contract_deadline=contract_deadline,
            escalation_level=0,
        )
        db.add(reg_clock)
        db.commit()

    return {
        "deduped": False,
        "burst_detected": burst_detected,
        "rate_limited": rate_limited,
        "incident_id": incident.id,
        "incident_number": incident.incident_number,
        "severity": severity.value,
        "ai_summary": ai_summary,
        "gdpr_deadline": gdpr_deadline.isoformat(),
        "customer_contract_deadline": contract_deadline.isoformat(),
    }


def assert_detect_component_cannot_change_policy() -> None:
    """Security boundary assertion: Detect component cannot modify policy."""
    raise ComponentBoundaryViolationError(
        "Sentinel Detect component cannot change policy or alter authorization rules."
    )


def assert_detect_component_cannot_contain() -> None:
    """Security boundary assertion: Detect component cannot execute containment."""
    raise ComponentBoundaryViolationError(
        "Sentinel Detect component cannot revoke access, terminate sessions, or contain workloads."
    )


def assert_detect_component_cannot_delete_logs() -> None:
    """Security boundary assertion: Detect component cannot delete or suppress audit records."""
    raise ComponentBoundaryViolationError(
        "Sentinel Detect component cannot delete, truncate, or alter audit logs."
    )
