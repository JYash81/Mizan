"""Post-activation regression detection against baseline and policy thresholds."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import (
    AlertInstance,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    RollbackPolicy,
)
from app.models.runtime import (
    GoldenTestOutcome,
    ReadinessState,
    RuntimeApplication,
    RuntimeSlot,
    SlotName,
)
from app.modules.observability.metric_registry import metric_registry


def detect_post_activation_regression(
    db: Session,
    runtime_app_id: str,
    policy: RollbackPolicy,
) -> tuple[bool, str]:
    """Inspect active slot health, error rates, latency p95, and firing alerts to detect regressions."""
    app = db.execute(
        select(RuntimeApplication).where(RuntimeApplication.id == runtime_app_id)
    ).scalar_one_or_none()

    if not app:
        return False, "Runtime application not found"

    active_slot_name = app.active_slot_name
    active_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == SlotName(active_slot_name),
        )
    ).scalar_one_or_none()

    if not active_slot:
        return False, "No active slot found"

    # 1. Check readiness & golden test status
    if active_slot.readiness_state == ReadinessState.UNHEALTHY:
        return True, f"Active slot '{active_slot_name}' reported UNHEALTHY readiness state."

    if active_slot.golden_test_status == GoldenTestOutcome.FAILED:
        return True, f"Golden test suite failed on active slot '{active_slot_name}'."

    # 2. Check Firing CRITICAL alerts on this site/slot
    firing_critical = (
        db.execute(
            select(AlertInstance)
            .join(AlertRule)
            .where(
                AlertInstance.customer_site_id == app.customer_site_id,
                AlertInstance.status == AlertStatus.FIRING,
                AlertRule.severity == AlertSeverity.CRITICAL,
            )
        )
        .scalars()
        .first()
    )

    if firing_critical:
        rule_name = firing_critical.rule.name if firing_critical.rule else "Critical Rule"
        return True, f"Critical alert '{rule_name}' is currently firing on customer site."

    # 3. Check error rate from in-memory metrics
    total_reqs = metric_registry.get_counter_value("runtime_requests_total")
    # In-memory histogram check for latency
    hist_snap = metric_registry.get_histogram_snapshot("runtime_request_duration_ms")
    if hist_snap and total_reqs > 0:
        for hist in hist_snap.values():
            if hist.count > 0:
                avg_lat = hist.total_sum / hist.count
                if avg_lat > policy.latency_p95_threshold_ms:
                    return (
                        True,
                        f"Average request latency ({round(avg_lat, 1)}ms) exceeded threshold ({policy.latency_p95_threshold_ms}ms).",
                    )

    return False, "Normal operation; no regression detected."
