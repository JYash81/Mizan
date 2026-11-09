"""Rule condition evaluation, instance state machine, and fingerprint deduplication."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.observability import (
    AlertEvent,
    AlertInstance,
    AlertRule,
    AlertStatus,
)
from app.modules.alerting.alert_silence_service import is_alert_silenced
from app.modules.alerting.schemas import AlertInstanceRead
from app.modules.observability.metric_registry import metric_registry


def evaluate_rule(
    db: Session,
    rule: AlertRule,
    current_value: float,
    labels: dict[str, str] | None = None,
    customer_site_id: str | None = None,
) -> AlertInstanceRead:
    """Evaluate a metric value against an alert rule condition and update instance state."""
    clean_labels = labels or {}
    lbl_str = json.dumps(clean_labels, sort_keys=True)
    raw_fp = f"{rule.id}:{customer_site_id or 'none'}:{lbl_str}"
    fingerprint = hashlib.sha256(raw_fp.encode("utf-8")).hexdigest()

    is_breached = _check_condition(rule.condition_operator, current_value, rule.threshold)
    now = datetime.now(UTC)

    # Locate or create alert instance
    instance = db.execute(
        select(AlertInstance).where(AlertInstance.fingerprint == fingerprint)
    ).scalar_one_or_none()

    if not instance:
        instance = AlertInstance(
            rule_id=rule.id,
            customer_site_id=customer_site_id,
            fingerprint=fingerprint,
            status=AlertStatus.NORMAL,
            current_value=current_value,
            breach_count=0,
            labels_json=lbl_str,
            annotations_json=json.dumps({"metric_key": rule.metric_key, "threshold": rule.threshold}),
            created_at=now,
            updated_at=now,
        )
        db.add(instance)
        db.flush()

    instance.current_value = current_value
    instance.updated_at = now

    if is_breached:
        instance.breach_count += 1
        instance.last_breached_at = now
        if not instance.first_breached_at:
            instance.first_breached_at = now

        # Check for active silence suppression
        silenced = is_alert_silenced(db, rule.id, customer_site_id)

        if silenced:
            if instance.status != AlertStatus.SILENCED:
                _transition_instance(db, instance, AlertStatus.SILENCED, "Suppressed by active silence window.")
        elif instance.breach_count >= rule.consecutive_breaches:
            if instance.status not in (AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED):
                instance.fired_at = now
                _transition_instance(
                    db,
                    instance,
                    AlertStatus.FIRING,
                    f"Threshold breached {instance.breach_count} times: {current_value} {rule.condition_operator} {rule.threshold}",
                )
                # Update Prometheus active alerts count gauge
                metric_registry.record_gauge(
                    "runtime_alerts_active",
                    1.0,
                    {"site_id": customer_site_id or "default", "severity": rule.severity.value},
                )
        else:
            if instance.status == AlertStatus.NORMAL:
                _transition_instance(db, instance, AlertStatus.PENDING, "First condition breach detected.")
    else:
        # Recovered
        if instance.status in (AlertStatus.FIRING, AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED, AlertStatus.SILENCED):
            instance.resolved_at = now
            instance.breach_count = 0
            _transition_instance(
                db,
                instance,
                AlertStatus.RESOLVED,
                f"Metric recovered to normal: {current_value} (threshold {rule.threshold})",
            )
            metric_registry.record_gauge(
                "runtime_alerts_active",
                0.0,
                {"site_id": customer_site_id or "default", "severity": rule.severity.value},
            )

    db.commit()
    db.refresh(instance)
    return _to_instance_read(instance)


def acknowledge_alert(
    db: Session,
    instance_id: str,
    actor_id: str,
    comment: str | None = None,
) -> AlertInstanceRead:
    """Operator acknowledgement of an active firing alert."""
    instance = db.execute(select(AlertInstance).where(AlertInstance.id == instance_id)).scalar_one_or_none()
    if not instance:
        raise ValueError(f"Alert instance '{instance_id}' not found.")

    now = datetime.now(UTC)
    instance.acknowledged_at = now
    instance.acknowledged_by = actor_id

    _transition_instance(
        db,
        instance,
        AlertStatus.ACKNOWLEDGED,
        comment or f"Acknowledged by operator {actor_id}",
        actor_id=actor_id,
    )

    db.commit()
    db.refresh(instance)
    return _to_instance_read(instance)


def list_alert_instances(
    db: Session,
    workspace_id: str | None = None,
    status: AlertStatus | None = None,
    customer_site_id: str | None = None,
    limit: int = 100,
) -> list[AlertInstanceRead]:
    """Retrieve filtered alert instances."""
    query = select(AlertInstance).join(AlertRule).order_by(desc(AlertInstance.updated_at))

    if workspace_id:
        query = query.where(AlertRule.workspace_id == workspace_id)
    if status:
        query = query.where(AlertInstance.status == status)
    if customer_site_id:
        query = query.where(AlertInstance.customer_site_id == customer_site_id)

    instances = db.execute(query.limit(limit)).scalars().all()
    return [_to_instance_read(inst) for inst in instances]


def _check_condition(op: str, val: float, threshold: float) -> bool:
    op_clean = op.upper().strip()
    if op_clean == "GT":
        return val > threshold
    if op_clean == "GTE":
        return val >= threshold
    if op_clean == "LT":
        return val < threshold
    if op_clean == "LTE":
        return val <= threshold
    if op_clean == "EQ":
        return val == threshold
    if op_clean == "NEQ":
        return val != threshold
    return False


def _transition_instance(
    db: Session,
    instance: AlertInstance,
    new_status: AlertStatus,
    reason: str,
    actor_id: str | None = None,
) -> None:
    prev = instance.status.value if hasattr(instance.status, "value") else str(instance.status)
    instance.status = new_status
    instance.updated_at = datetime.now(UTC)

    event = AlertEvent(
        alert_instance_id=instance.id,
        previous_status=prev,
        new_status=new_status.value,
        transition_reason=reason,
        actor_id=actor_id,
        created_at=datetime.now(UTC),
    )
    db.add(event)


def _to_instance_read(i: AlertInstance) -> AlertInstanceRead:
    return AlertInstanceRead(
        id=i.id,
        rule_id=i.rule_id,
        customer_site_id=i.customer_site_id,
        fingerprint=i.fingerprint,
        status=i.status,
        current_value=i.current_value,
        breach_count=i.breach_count,
        first_breached_at=i.first_breached_at,
        last_breached_at=i.last_breached_at,
        fired_at=i.fired_at,
        acknowledged_at=i.acknowledged_at,
        acknowledged_by=i.acknowledged_by,
        resolved_at=i.resolved_at,
        labels=i.labels,
        annotations=i.annotations,
        created_at=i.created_at,
        updated_at=i.updated_at,
    )
