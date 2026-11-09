"""SLO lifecycle and historical snapshot management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.observability import ServiceLevelObjective, SliSnapshot
from app.modules.observability.metric_registry import metric_registry
from app.modules.slo.schemas import SliSnapshotRead, SloCreate, SloRead
from app.modules.slo.sli_calculator import compute_sli_and_budget


def create_slo(
    db: Session,
    workspace_id: str,
    payload: SloCreate,
) -> SloRead:
    """Create a Service Level Objective target."""
    now = datetime.now(UTC)
    slo = ServiceLevelObjective(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        target_percentage=payload.target_percentage,
        rolling_window_days=payload.rolling_window_days,
        metric_key=payload.metric_key,
        good_events_definition=payload.good_events_definition,
        is_enabled=payload.is_enabled,
        created_at=now,
        updated_at=now,
    )
    db.add(slo)
    db.commit()
    db.refresh(slo)
    return _to_slo_read(slo)


def list_slos(
    db: Session,
    workspace_id: str,
) -> list[SloRead]:
    """Retrieve all SLOs for a workspace."""
    slos = (
        db.execute(select(ServiceLevelObjective).where(ServiceLevelObjective.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_slo_read(s) for s in slos]


def record_snapshot(
    db: Session,
    slo_id: str,
    total_events: int,
    good_events: int,
    customer_site_id: str | None = None,
) -> SliSnapshotRead:
    """Calculate and record a point-in-time SLI and error budget snapshot."""
    slo = db.execute(select(ServiceLevelObjective).where(ServiceLevelObjective.id == slo_id)).scalar_one_or_none()
    if not slo:
        raise ValueError(f"SLO '{slo_id}' not found.")

    sli, budget, has_data, burn_rate = compute_sli_and_budget(
        slo.target_percentage, total_events, good_events
    )

    now = datetime.now(UTC)
    start = now - timedelta(days=slo.rolling_window_days)

    snapshot = SliSnapshot(
        slo_id=slo.id,
        customer_site_id=customer_site_id,
        window_start=start,
        window_end=now,
        total_events=total_events,
        good_events=good_events,
        current_sli_percentage=sli,
        error_budget_remaining_percentage=budget,
        has_sufficient_data=has_data,
        created_at=now,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    # Expose current budget percent to Prometheus gauge
    metric_registry.record_gauge(
        "runtime_slo_error_budget_percent",
        budget,
        {"slo_id": slo.id, "workspace_id": slo.workspace_id},
    )

    return _to_snapshot_read(snapshot, burn_rate)


def get_latest_snapshot(
    db: Session,
    slo_id: str,
) -> SliSnapshotRead | None:
    """Retrieve the most recent calculated snapshot for an SLO."""
    snapshot = (
        db.execute(
            select(SliSnapshot)
            .where(SliSnapshot.slo_id == slo_id)
            .order_by(desc(SliSnapshot.created_at))
        )
        .scalars()
        .first()
    )
    if not snapshot:
        return None

    slo = db.execute(select(ServiceLevelObjective).where(ServiceLevelObjective.id == slo_id)).scalar_one_or_none()
    target = slo.target_percentage if slo else 99.5
    _, _, _, burn_rate = compute_sli_and_budget(target, snapshot.total_events, snapshot.good_events)

    return _to_snapshot_read(snapshot, burn_rate)


def _to_slo_read(s: ServiceLevelObjective) -> SloRead:
    return SloRead(
        id=s.id,
        workspace_id=s.workspace_id,
        name=s.name,
        description=s.description,
        target_percentage=s.target_percentage,
        rolling_window_days=s.rolling_window_days,
        metric_key=s.metric_key,
        good_events_definition=s.good_events_definition,
        is_enabled=s.is_enabled,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_snapshot_read(sn: SliSnapshot, burn_rate: float = 1.0) -> SliSnapshotRead:
    return SliSnapshotRead(
        id=sn.id,
        slo_id=sn.slo_id,
        customer_site_id=sn.customer_site_id,
        window_start=sn.window_start,
        window_end=sn.window_end,
        total_events=sn.total_events,
        good_events=sn.good_events,
        current_sli_percentage=sn.current_sli_percentage,
        error_budget_remaining_percentage=sn.error_budget_remaining_percentage,
        has_sufficient_data=sn.has_sufficient_data,
        burn_rate=burn_rate,
        created_at=sn.created_at,
    )
