"""Alert Rule Registry and standard rule seeding."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import AlertRule, AlertSeverity
from app.modules.alerting.schemas import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate

DEFAULT_ALERT_RULE_TEMPLATES = [
    {
        "name": "HighRequestErrorRate",
        "description": "Triggered when 5xx HTTP request error percentage exceeds 5%.",
        "metric_key": "runtime_requests_total",
        "condition_operator": "GT",
        "threshold": 5.0,
        "duration_seconds": 60,
        "consecutive_breaches": 1,
        "severity": AlertSeverity.CRITICAL,
        "cooldown_seconds": 300,
        "target_slot": "ACTIVE",
    },
    {
        "name": "HighInferenceLatencyP95",
        "description": "Triggered when p95 inference latency exceeds 2000 milliseconds.",
        "metric_key": "runtime_request_duration_ms",
        "condition_operator": "GT",
        "threshold": 2000.0,
        "duration_seconds": 120,
        "consecutive_breaches": 2,
        "severity": AlertSeverity.WARNING,
        "cooldown_seconds": 300,
        "target_slot": "ACTIVE",
    },
    {
        "name": "SlotUnhealthyOrUnready",
        "description": "Triggered when the active runtime slot readiness falls below 1 (unready).",
        "metric_key": "runtime_readiness_state",
        "condition_operator": "LT",
        "threshold": 1.0,
        "duration_seconds": 60,
        "consecutive_breaches": 1,
        "severity": AlertSeverity.CRITICAL,
        "cooldown_seconds": 180,
        "target_slot": "ACTIVE",
    },
    {
        "name": "GoldenTestFailure",
        "description": "Triggered when latest acceptance golden test outcome fails.",
        "metric_key": "runtime_golden_test_status",
        "condition_operator": "LT",
        "threshold": 1.0,
        "duration_seconds": 30,
        "consecutive_breaches": 1,
        "severity": AlertSeverity.CRITICAL,
        "cooldown_seconds": 300,
        "target_slot": "ANY",
    },
    {
        "name": "AgentHeartbeatStale",
        "description": "Triggered when customer Site Agent heartbeat ceases.",
        "metric_key": "runtime_site_agent_heartbeat_status",
        "condition_operator": "LT",
        "threshold": 1.0,
        "duration_seconds": 180,
        "consecutive_breaches": 1,
        "severity": AlertSeverity.WARNING,
        "cooldown_seconds": 300,
        "target_slot": "ANY",
    },
    {
        "name": "MemoryUsageHigh",
        "description": "Triggered when runtime system memory exceeds 85% capacity.",
        "metric_key": "runtime_cpu_usage_percent",
        "condition_operator": "GT",
        "threshold": 85.0,
        "duration_seconds": 300,
        "consecutive_breaches": 3,
        "severity": AlertSeverity.WARNING,
        "cooldown_seconds": 600,
        "target_slot": "ANY",
    },
]


def seed_default_alert_rules(
    db: Session,
    workspace_id: str,
    actor_id: str,
) -> list[AlertRuleRead]:
    """Seed standard operational alert rules for a workspace if not already present."""
    existing_rules = (
        db.execute(select(AlertRule).where(AlertRule.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    existing_names = {r.name for r in existing_rules}

    created: list[AlertRule] = []
    now = datetime.now(UTC)

    for tmpl in DEFAULT_ALERT_RULE_TEMPLATES:
        if tmpl["name"] in existing_names:
            continue
        rule = AlertRule(
            workspace_id=workspace_id,
            name=tmpl["name"],
            description=tmpl["description"],
            metric_key=tmpl["metric_key"],
            condition_operator=tmpl["condition_operator"],
            threshold=tmpl["threshold"],
            duration_seconds=tmpl["duration_seconds"],
            consecutive_breaches=tmpl["consecutive_breaches"],
            severity=tmpl["severity"],
            is_enabled=True,
            cooldown_seconds=tmpl["cooldown_seconds"],
            target_slot=tmpl["target_slot"],
            created_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        created.append(rule)

    if created:
        db.commit()
        for r in created:
            db.refresh(r)

    all_rules = (
        db.execute(select(AlertRule).where(AlertRule.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_rule_read(r) for r in all_rules]


def create_alert_rule(
    db: Session,
    workspace_id: str,
    payload: AlertRuleCreate,
    actor_id: str,
) -> AlertRuleRead:
    """Create a user-defined alert rule."""
    now = datetime.now(UTC)
    rule = AlertRule(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        metric_key=payload.metric_key,
        condition_operator=payload.condition_operator,
        threshold=payload.threshold,
        duration_seconds=payload.duration_seconds,
        consecutive_breaches=payload.consecutive_breaches,
        severity=payload.severity,
        is_enabled=payload.is_enabled,
        cooldown_seconds=payload.cooldown_seconds,
        target_slot=payload.target_slot,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _to_rule_read(rule)


def list_alert_rules(db: Session, workspace_id: str) -> list[AlertRuleRead]:
    """Retrieve all alert rules for a workspace."""
    rules = (
        db.execute(select(AlertRule).where(AlertRule.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_rule_read(r) for r in rules]


def update_alert_rule(
    db: Session,
    rule_id: str,
    payload: AlertRuleUpdate,
) -> AlertRuleRead:
    """Update an existing alert rule threshold or configuration."""
    rule = db.execute(select(AlertRule).where(AlertRule.id == rule_id)).scalar_one_or_none()
    if not rule:
        raise ValueError(f"Alert rule '{rule_id}' not found.")

    if payload.name is not None:
        rule.name = payload.name
    if payload.description is not None:
        rule.description = payload.description
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.duration_seconds is not None:
        rule.duration_seconds = payload.duration_seconds
    if payload.consecutive_breaches is not None:
        rule.consecutive_breaches = payload.consecutive_breaches
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled
    if payload.cooldown_seconds is not None:
        rule.cooldown_seconds = payload.cooldown_seconds

    rule.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(rule)
    return _to_rule_read(rule)


def delete_alert_rule(db: Session, rule_id: str) -> None:
    """Delete an alert rule and associated instances."""
    rule = db.execute(select(AlertRule).where(AlertRule.id == rule_id)).scalar_one_or_none()
    if rule:
        db.delete(rule)
        db.commit()


def _to_rule_read(r: AlertRule) -> AlertRuleRead:
    return AlertRuleRead(
        id=r.id,
        workspace_id=r.workspace_id,
        name=r.name,
        description=r.description,
        metric_key=r.metric_key,
        condition_operator=r.condition_operator,
        threshold=r.threshold,
        duration_seconds=r.duration_seconds,
        consecutive_breaches=r.consecutive_breaches,
        severity=r.severity,
        is_enabled=r.is_enabled,
        cooldown_seconds=r.cooldown_seconds,
        target_slot=r.target_slot,
        created_by=r.created_by,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )
