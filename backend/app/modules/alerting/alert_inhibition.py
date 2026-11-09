"""Alert inhibition and secondary alert suppression logic."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import AlertEvent, AlertInstance, AlertRule, AlertStatus

PRIMARY_OUTAGE_RULE_KEYS = {
    "SlotUnhealthyOrUnready",
    "AgentHeartbeatStale",
    "runtime_readiness_state",
    "runtime_site_agent_heartbeat_status",
}

SECONDARY_SYMPTOM_KEYS = {
    "HighInferenceLatencyP95",
    "runtime_request_duration_ms",
    "HighRequestErrorRate",
}


def apply_alert_inhibition(
    db: Session,
    customer_site_id: str,
) -> list[str]:
    """Inhibit secondary symptom alerts if a primary root-cause outage alert is firing."""
    firing_instances = (
        db.execute(
            select(AlertInstance)
            .join(AlertRule)
            .where(
                AlertInstance.customer_site_id == customer_site_id,
                AlertInstance.status == AlertStatus.FIRING,
            )
        )
        .scalars()
        .all()
    )

    has_primary_outage = False
    for inst in firing_instances:
        rule_name = inst.rule.name if inst.rule else ""
        metric_key = inst.rule.metric_key if inst.rule else ""
        if rule_name in PRIMARY_OUTAGE_RULE_KEYS or metric_key in PRIMARY_OUTAGE_RULE_KEYS:
            has_primary_outage = True
            break

    suppressed_ids: list[str] = []
    if not has_primary_outage:
        return suppressed_ids

    # Suppress secondary firing instances
    for inst in firing_instances:
        rule_name = inst.rule.name if inst.rule else ""
        metric_key = inst.rule.metric_key if inst.rule else ""
        if rule_name in SECONDARY_SYMPTOM_KEYS or metric_key in SECONDARY_SYMPTOM_KEYS:
            inst.status = AlertStatus.SUPPRESSED
            inst.updated_at = datetime.now(UTC)

            event = AlertEvent(
                alert_instance_id=inst.id,
                previous_status=AlertStatus.FIRING.value,
                new_status=AlertStatus.SUPPRESSED.value,
                transition_reason="Inhibited: Primary site outage alert is firing.",
                created_at=datetime.now(UTC),
            )
            db.add(event)
            suppressed_ids.append(inst.id)

    if suppressed_ids:
        db.commit()

    return suppressed_ids
