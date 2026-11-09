"""Alert Silence management and active suppression checking."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import AlertSilence
from app.modules.alerting.schemas import AlertSilenceCreate, AlertSilenceRead


def create_alert_silence(
    db: Session,
    workspace_id: str,
    payload: AlertSilenceCreate,
    actor_id: str,
) -> AlertSilenceRead:
    """Create a time-bounded silence window for an alert rule or site."""
    if payload.ends_at <= payload.starts_at:
        raise ValueError("Silence end time must be after start time.")

    silence = AlertSilence(
        workspace_id=workspace_id,
        rule_id=payload.rule_id,
        customer_site_id=payload.customer_site_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        reason=payload.reason,
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    db.add(silence)
    db.commit()
    db.refresh(silence)
    return _to_silence_read(silence)


def list_alert_silences(
    db: Session,
    workspace_id: str,
) -> list[AlertSilenceRead]:
    """Retrieve all silences defined for a workspace."""
    silences = (
        db.execute(select(AlertSilence).where(AlertSilence.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_silence_read(s) for s in silences]


def is_alert_silenced(
    db: Session,
    rule_id: str,
    customer_site_id: str | None = None,
) -> bool:
    """Check whether an active silence window currently matches this rule or site."""
    now = datetime.now(UTC)
    query = select(AlertSilence).where(
        AlertSilence.starts_at <= now,
        AlertSilence.ends_at >= now,
    )

    silences = db.execute(query).scalars().all()
    for s in silences:
        # Check rule match
        rule_match = s.rule_id is None or s.rule_id == rule_id
        # Check site match
        site_match = s.customer_site_id is None or s.customer_site_id == customer_site_id
        if rule_match and site_match:
            return True

    return False


def _to_silence_read(s: AlertSilence) -> AlertSilenceRead:
    return AlertSilenceRead(
        id=s.id,
        workspace_id=s.workspace_id,
        rule_id=s.rule_id,
        customer_site_id=s.customer_site_id,
        starts_at=s.starts_at,
        ends_at=s.ends_at,
        reason=s.reason,
        created_by=s.created_by,
        created_at=s.created_at,
    )
