"""Blue/Green runtime slot management, staging, promotion, and rollback service."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact_registry import ModelVersion
from app.models.runtime import (
    GoldenTestOutcome,
    ReadinessState,
    RuntimeActivationEvent,
    RuntimeApplication,
    RuntimeSlot,
    SlotName,
    SlotStatus,
)
from app.modules.runtime.exceptions import (
    InvalidSlotStateTransitionError,
    PackageVerificationError,
    SlotActivationBlockedError,
    SlotNotFoundError,
)
from app.modules.runtime.schemas import (
    RuntimeActivationEventRead,
    RuntimeSlotRead,
    SlotActivateRequest,
    SlotRollbackRequest,
    SlotStageRequest,
)


def get_application_slots(
    db: Session,
    runtime_app_id: str,
) -> list[RuntimeSlotRead]:
    """Retrieve both Blue and Green slots for an installed application."""
    slots = (
        db.execute(
            select(RuntimeSlot)
            .where(RuntimeSlot.runtime_application_id == runtime_app_id)
            .order_by(RuntimeSlot.slot_name)
        )
        .scalars()
        .all()
    )
    return [_to_slot_read(s) for s in slots]


def stage_candidate_to_slot(
    db: Session,
    runtime_app_id: str,
    payload: SlotStageRequest,
) -> RuntimeSlotRead:
    """Stage a candidate package into the inactive blue/green slot."""
    app = db.execute(
        select(RuntimeApplication).where(RuntimeApplication.id == runtime_app_id)
    ).scalar_one_or_none()

    if not app:
        raise SlotNotFoundError(f"Runtime application '{runtime_app_id}' not found.")

    # Determine inactive slot
    current_active_slot_name = app.active_slot_name
    if payload.target_slot_name:
        target_slot_name = payload.target_slot_name
    else:
        # Auto-pick the inactive slot
        target_slot_name = (
            SlotName.SLOT_B if current_active_slot_name == SlotName.SLOT_A.value else SlotName.SLOT_A
        )

    # Fetch target slot
    slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == target_slot_name,
        )
    ).scalar_one_or_none()

    if not slot:
        raise SlotNotFoundError(f"Slot '{target_slot_name}' does not exist for this application.")

    # Verify model version exists to retrieve release_manifest_digest
    model_version = db.execute(
        select(ModelVersion).where(ModelVersion.id == payload.model_version_id)
    ).scalar_one_or_none()

    if not model_version:
        raise PackageVerificationError(f"Model version '{payload.model_version_id}' not found.")

    # Unload-and-load staging semantics for memory-limited environments
    # Reset previous candidate state
    now = datetime.now(UTC)
    slot.app_version_id = payload.app_version_id
    slot.model_version_id = payload.model_version_id
    slot.release_manifest_digest = model_version.release_manifest_digest or "MOCK_MANIFEST_DIGEST"
    slot.engine_adapter_key = payload.engine_adapter_key
    slot.configuration_snapshot_json = json.dumps(payload.configuration)
    slot.status = SlotStatus.STAGED
    slot.readiness_state = ReadinessState.LOADING
    slot.golden_test_status = GoldenTestOutcome.NOT_RUN
    slot.last_golden_test_run_id = None
    slot.staged_at = now

    db.commit()
    db.refresh(slot)

    return _to_slot_read(slot)


def promote_slot(
    db: Session,
    runtime_app_id: str,
    payload: SlotActivateRequest,
    actor_id: str,
) -> RuntimeSlotRead:
    """Promote a staged candidate slot to active traffic serving. Gated by Golden Tests."""
    app = db.execute(
        select(RuntimeApplication).where(RuntimeApplication.id == runtime_app_id)
    ).scalar_one_or_none()

    if not app:
        raise SlotNotFoundError(f"Runtime application '{runtime_app_id}' not found.")

    target_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == payload.slot_name,
        )
    ).scalar_one_or_none()

    if not target_slot:
        raise SlotNotFoundError(f"Slot '{payload.slot_name}' not found.")

    # Invariant: slot must not already be active
    if app.active_slot_name == payload.slot_name.value and target_slot.status == SlotStatus.ACTIVE:
        return _to_slot_read(target_slot)

    # Invariant: Golden Tests MUST be PASSED
    if target_slot.golden_test_status != GoldenTestOutcome.PASSED:
        raise SlotActivationBlockedError(
            f"Cannot activate slot '{payload.slot_name}': golden test status is "
            f"'{target_slot.golden_test_status}', but MUST be 'PASSED'."
        )

    # Invariant: readiness state must be READY
    if target_slot.readiness_state != ReadinessState.READY:
        raise SlotActivationBlockedError(
            f"Cannot activate slot '{payload.slot_name}': readiness state is "
            f"'{target_slot.readiness_state}', not 'READY'."
        )

    # Identify currently active slot
    prev_active_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == SlotName(app.active_slot_name),
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)

    # Switch active slots atomically
    if prev_active_slot and prev_active_slot.id != target_slot.id:
        prev_active_slot.status = SlotStatus.STAGED  # Preserved for instant rollback

    target_slot.status = SlotStatus.ACTIVE
    target_slot.activated_at = now
    app.active_slot_name = payload.slot_name.value
    app.app_version_id = target_slot.app_version_id

    # Append immutable activation event
    event = RuntimeActivationEvent(
        customer_site_id=app.customer_site_id,
        runtime_application_id=app.id,
        previous_slot_name=prev_active_slot.slot_name.value if prev_active_slot else "NONE",
        new_slot_name=payload.slot_name.value,
        model_version_id=target_slot.model_version_id or "UNKNOWN",
        app_version_id=target_slot.app_version_id or "UNKNOWN",
        release_manifest_digest=target_slot.release_manifest_digest or "UNKNOWN",
        golden_test_run_id=target_slot.last_golden_test_run_id,
        actor_id=actor_id,
        switch_reason=payload.reason,
        created_at=now,
    )
    db.add(event)

    db.commit()
    db.refresh(target_slot)
    return _to_slot_read(target_slot)


def rollback_slot(
    db: Session,
    runtime_app_id: str,
    payload: SlotRollbackRequest,
    actor_id: str,
) -> RuntimeSlotRead:
    """Manually rollback active traffic serving to the alternate slot."""
    app = db.execute(
        select(RuntimeApplication).where(RuntimeApplication.id == runtime_app_id)
    ).scalar_one_or_none()

    if not app:
        raise SlotNotFoundError(f"Runtime application '{runtime_app_id}' not found.")

    current_slot_name = SlotName(app.active_slot_name)
    rollback_slot_name = (
        SlotName.SLOT_B if current_slot_name == SlotName.SLOT_A else SlotName.SLOT_A
    )

    current_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == current_slot_name,
        )
    ).scalar_one_or_none()

    rollback_slot = db.execute(
        select(RuntimeSlot).where(
            RuntimeSlot.runtime_application_id == app.id,
            RuntimeSlot.slot_name == rollback_slot_name,
        )
    ).scalar_one_or_none()

    if not rollback_slot or not rollback_slot.model_version_id:
        raise InvalidSlotStateTransitionError(
            f"Cannot rollback: alternate slot '{rollback_slot_name}' has no previous configuration."
        )

    now = datetime.now(UTC)

    if current_slot:
        current_slot.status = SlotStatus.STAGED

    rollback_slot.status = SlotStatus.ACTIVE
    rollback_slot.activated_at = now
    app.active_slot_name = rollback_slot_name.value
    app.app_version_id = rollback_slot.app_version_id

    # Append immutable audit event
    event = RuntimeActivationEvent(
        customer_site_id=app.customer_site_id,
        runtime_application_id=app.id,
        previous_slot_name=current_slot_name.value,
        new_slot_name=rollback_slot_name.value,
        model_version_id=rollback_slot.model_version_id or "UNKNOWN",
        app_version_id=rollback_slot.app_version_id or "UNKNOWN",
        release_manifest_digest=rollback_slot.release_manifest_digest or "UNKNOWN",
        golden_test_run_id=rollback_slot.last_golden_test_run_id,
        actor_id=actor_id,
        switch_reason=f"ROLLBACK: {payload.reason}",
        created_at=now,
    )
    db.add(event)

    db.commit()
    db.refresh(rollback_slot)
    return _to_slot_read(rollback_slot)


def list_activation_events(
    db: Session,
    runtime_app_id: str,
) -> list[RuntimeActivationEventRead]:
    """Retrieve append-only audit trail of slot activation events."""
    events = (
        db.execute(
            select(RuntimeActivationEvent)
            .where(RuntimeActivationEvent.runtime_application_id == runtime_app_id)
            .order_by(RuntimeActivationEvent.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [RuntimeActivationEventRead.model_validate(e) for e in events]


def _to_slot_read(slot: RuntimeSlot) -> RuntimeSlotRead:
    return RuntimeSlotRead(
        id=slot.id,
        runtime_application_id=slot.runtime_application_id,
        slot_name=slot.slot_name,
        app_version_id=slot.app_version_id,
        model_version_id=slot.model_version_id,
        release_manifest_digest=slot.release_manifest_digest,
        status=slot.status,
        readiness_state=slot.readiness_state,
        golden_test_status=slot.golden_test_status,
        last_golden_test_run_id=slot.last_golden_test_run_id,
        engine_adapter_key=slot.engine_adapter_key,
        configuration_snapshot=slot.configuration_snapshot,
        staged_at=slot.staged_at,
        activated_at=slot.activated_at,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )
