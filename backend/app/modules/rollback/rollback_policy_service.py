"""Rollback Policy management with safe defaults (MANUAL_ONLY)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import RollbackMode, RollbackPolicy
from app.modules.rollback.schemas import RollbackPolicyRead, RollbackPolicyUpdate


def get_or_create_rollback_policy(
    db: Session,
    workspace_id: str,
    runtime_application_id: str | None = None,
    actor_id: str | None = None,
) -> RollbackPolicyRead:
    """Retrieve or initialize a rollback policy for a workspace or application."""
    query = select(RollbackPolicy).where(RollbackPolicy.workspace_id == workspace_id)
    if runtime_application_id:
        query = query.where(RollbackPolicy.runtime_application_id == runtime_application_id)

    policy = db.execute(query).scalar_one_or_none()

    if not policy:
        now = datetime.now(UTC)
        effective_actor_id = actor_id
        if not effective_actor_id:
            from app.models.organization import Workspace
            ws = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
            if ws and ws.created_by:
                effective_actor_id = ws.created_by
            else:
                from app.models.identity import User
                first_user_id = db.execute(select(User.id)).scalars().first()
                effective_actor_id = first_user_id or "system"

        policy = RollbackPolicy(
            workspace_id=workspace_id,
            runtime_application_id=runtime_application_id,
            mode=RollbackMode.MANUAL_ONLY,  # Invariant: Never default to aggressive automatic rollback
            evaluation_window_seconds=300,
            error_rate_threshold_percentage=5.0,
            latency_p95_threshold_ms=2000.0,
            cooldown_seconds=600,
            max_automatic_attempts_per_release=1,
            require_golden_test_pass=True,
            require_gate3_active=True,
            created_by=effective_actor_id,
            created_at=now,
            updated_at=now,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

    return _to_policy_read(policy)


def update_rollback_policy(
    db: Session,
    policy_id: str,
    payload: RollbackPolicyUpdate,
) -> RollbackPolicyRead:
    """Update rollback criteria and operational mode."""
    policy = db.execute(select(RollbackPolicy).where(RollbackPolicy.id == policy_id)).scalar_one_or_none()
    if not policy:
        raise ValueError(f"Rollback policy '{policy_id}' not found.")

    if payload.mode is not None:
        policy.mode = payload.mode
    if payload.evaluation_window_seconds is not None:
        policy.evaluation_window_seconds = payload.evaluation_window_seconds
    if payload.error_rate_threshold_percentage is not None:
        policy.error_rate_threshold_percentage = payload.error_rate_threshold_percentage
    if payload.latency_p95_threshold_ms is not None:
        policy.latency_p95_threshold_ms = payload.latency_p95_threshold_ms
    if payload.cooldown_seconds is not None:
        policy.cooldown_seconds = payload.cooldown_seconds
    if payload.max_automatic_attempts_per_release is not None:
        policy.max_automatic_attempts_per_release = payload.max_automatic_attempts_per_release
    if payload.require_golden_test_pass is not None:
        policy.require_golden_test_pass = payload.require_golden_test_pass
    if payload.require_gate3_active is not None:
        policy.require_gate3_active = payload.require_gate3_active

    policy.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(policy)
    return _to_policy_read(policy)


def list_rollback_policies(
    db: Session,
    workspace_id: str,
) -> list[RollbackPolicyRead]:
    """Retrieve all rollback policies configured in a workspace."""
    policies = (
        db.execute(select(RollbackPolicy).where(RollbackPolicy.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_policy_read(p) for p in policies]


def _to_policy_read(p: RollbackPolicy) -> RollbackPolicyRead:
    return RollbackPolicyRead(
        id=p.id,
        workspace_id=p.workspace_id,
        runtime_application_id=p.runtime_application_id,
        mode=p.mode,
        evaluation_window_seconds=p.evaluation_window_seconds,
        error_rate_threshold_percentage=p.error_rate_threshold_percentage,
        latency_p95_threshold_ms=p.latency_p95_threshold_ms,
        cooldown_seconds=p.cooldown_seconds,
        max_automatic_attempts_per_release=p.max_automatic_attempts_per_release,
        require_golden_test_pass=p.require_golden_test_pass,
        require_gate3_active=p.require_gate3_active,
        created_by=p.created_by,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
