"""Safety validator for target rollback slots, Gate 3 attestation, and anti-flapping."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.artifact_registry import Gate3Approval, Gate3Decision, Gate3Revocation
from app.models.observability import RollbackExecutionEvent, RollbackPolicy
from app.models.runtime import RuntimeApplication, RuntimeSlot, SlotName
from app.modules.rollback.schemas import RollbackEligibilityCheckResult


def check_rollback_eligibility(
    db: Session,
    runtime_app_id: str,
    policy: RollbackPolicy | None = None,
) -> RollbackEligibilityCheckResult:
    """Validate whether the alternate runtime slot satisfies all safety criteria for traffic rollback."""
    app = db.execute(
        select(RuntimeApplication).where(RuntimeApplication.id == runtime_app_id)
    ).scalar_one_or_none()

    if not app:
        return RollbackEligibilityCheckResult(
            is_eligible=False,
            reasons=[f"Runtime application '{runtime_app_id}' not found."],
            current_slot_name="UNKNOWN",
            target_slot_name="UNKNOWN",
        )

    current_slot_name = app.active_slot_name
    target_slot_name = (
        SlotName.SLOT_B.value if current_slot_name == SlotName.SLOT_A.value else SlotName.SLOT_A.value
    )

    current_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == SlotName(current_slot_name),
        )
    ).scalar_one_or_none()

    target_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == SlotName(target_slot_name),
        )
    ).scalar_one_or_none()

    reasons: list[str] = []

    if not target_slot or not target_slot.model_version_id:
        return RollbackEligibilityCheckResult(
            is_eligible=False,
            reasons=[f"Alternate slot '{target_slot_name}' has no previous model configuration."],
            current_slot_name=current_slot_name,
            target_slot_name=target_slot_name,
        )

    target_model_id = target_slot.model_version_id

    # 1. Anti-Revocation check: Verify target release was NOT revoked
    revocation = db.execute(
        select(Gate3Revocation).where(Gate3Revocation.model_version_id == target_model_id)
    ).scalar_one_or_none()

    target_is_revoked = revocation is not None
    if target_is_revoked:
        reasons.append(
            f"Safety Violation: Target model version '{target_model_id}' was REVOKED/withdrawn via Gate 3."
        )

    # 2. Gate 3 Approval check
    target_is_approved = False
    if policy is None or policy.require_gate3_active:
        gate3 = db.execute(
            select(Gate3Approval).where(
                Gate3Approval.model_version_id == target_model_id,
                Gate3Approval.decision == Gate3Decision.APPROVED,
            )
        ).scalar_one_or_none()
        target_is_approved = gate3 is not None
        if not target_is_approved:
            reasons.append(
                f"Safety Violation: Target model version '{target_model_id}' lacks valid Gate 3 human approval."
            )
    else:
        target_is_approved = True

    # 3. Anti-Flapping check: Cooldown and Max Attempts
    flapping_detected = False
    if policy:
        recent_events = (
            db.execute(
                select(RollbackExecutionEvent)
                .where(RollbackExecutionEvent.runtime_application_id == app.id)
                .order_by(desc(RollbackExecutionEvent.created_at))
            )
            .scalars()
            .all()
        )

        now = datetime.now(UTC)
        if recent_events:
            last_event = recent_events[0]
            # Cooldown check
            created_at_utc = (
                last_event.created_at.replace(tzinfo=UTC)
                if last_event.created_at.tzinfo is None
                else last_event.created_at.astimezone(UTC)
            )
            elapsed_seconds = (now - created_at_utc).total_seconds()
            if elapsed_seconds < policy.cooldown_seconds:
                flapping_detected = True
                remaining = int(policy.cooldown_seconds - elapsed_seconds)
                reasons.append(
                    f"Anti-Flapping: Cooldown in effect. Must wait {remaining}s before another rollback."
                )

            # Max attempts per release
            curr_model_id = current_slot.model_version_id if current_slot else None
            if curr_model_id:
                attempts_for_curr = sum(
                    1
                    for e in recent_events
                    if e.from_model_version_id == curr_model_id and e.status == "SUCCESS"
                )
                if attempts_for_curr >= policy.max_automatic_attempts_per_release:
                    flapping_detected = True
                    reasons.append(
                        f"Anti-Flapping: Max rollback attempts ({policy.max_automatic_attempts_per_release}) reached for release '{curr_model_id}'."
                    )

    is_eligible = (not target_is_revoked) and target_is_approved and (not flapping_detected)

    return RollbackEligibilityCheckResult(
        is_eligible=is_eligible,
        reasons=reasons,
        current_slot_name=current_slot_name,
        target_slot_name=target_slot_name,
        target_model_version_id=target_model_id,
        target_is_gate3_approved=target_is_approved,
        target_is_revoked=target_is_revoked,
        flapping_detected=flapping_detected,
    )
