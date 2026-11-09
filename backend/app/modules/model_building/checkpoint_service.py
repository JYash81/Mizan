"""Checkpoint management, atomic persistence, and resumption validation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_building import (
    ModelBuildCheckpoint,
    ModelBuildEvent,
    ModelBuildRun,
    ModelBuildStatus,
)
from app.modules.storage.provider import StorageBucket
from app.modules.storage.service import get_storage_provider


class CheckpointError(Exception):
    """Raised when checkpoint creation or resumption validation fails."""


def record_checkpoint(
    db: Session,
    build_run: ModelBuildRun,
    checkpoint_number: int,
    step_number: int,
    epoch: float,
    metrics: dict[str, Any],
    checkpoint_bytes: bytes,
) -> ModelBuildCheckpoint:
    """Atomically store checkpoint data and persist metadata record in database."""
    storage = get_storage_provider()
    sha256_hash = hashlib.sha256(checkpoint_bytes).hexdigest()
    storage_key = (
        f"workspaces/{build_run.workspace_id}/builds/{build_run.id}/checkpoints/ckpt_{checkpoint_number:04d}_{step_number}.bin"
    )

    storage.put_object(
        bucket=StorageBucket.ARTIFACTS,
        key=storage_key,
        data=checkpoint_bytes,
        content_type="application/octet-stream",
    )

    ckpt = ModelBuildCheckpoint(
        build_run_id=build_run.id,
        checkpoint_number=checkpoint_number,
        step_number=step_number,
        epoch=epoch,
        storage_reference=storage_key,
        sha256=sha256_hash,
        configuration_digest=build_run.manifest_digest,
        metrics_json=json.dumps(metrics),
    )
    db.add(ckpt)

    event = ModelBuildEvent(
        build_run_id=build_run.id,
        event_type="CHECKPOINT_SAVED",
        message=f"Checkpoint #{checkpoint_number} saved at step {step_number} (SHA-256: {sha256_hash[:12]}...).",
        metadata_json=json.dumps(
            {"checkpoint_number": checkpoint_number, "step": step_number, "sha256": sha256_hash}
        ),
    )
    db.add(event)
    db.commit()
    db.refresh(ckpt)
    return ckpt


def validate_resume_compatibility(
    build_run: ModelBuildRun,
    proposed_manifest_digest: str,
    proposed_base_revision: str,
    proposed_dataset_digest: str | None = None,
) -> bool:
    """Verify that a resumed session matches the exact base model, dataset, and recipe.

    Raises CheckpointError if any source configuration has changed.
    """
    if build_run.status not in (
        ModelBuildStatus.INTERRUPTED,
        ModelBuildStatus.RESUMABLE,
        ModelBuildStatus.RUNNING,
    ):
        raise CheckpointError(
            f"Build run '{build_run.id}' is in status '{build_run.status.value}', cannot resume."
        )

    if build_run.manifest_digest != proposed_manifest_digest:
        raise CheckpointError(
            "Resume rejected: Proposed manifest digest does not match original build manifest digest."
        )

    if build_run.source_revision != proposed_base_revision:
        raise CheckpointError(
            f"Resume rejected: Base model revision mismatch ('{proposed_base_revision}' != '{build_run.source_revision}')."
        )

    if proposed_dataset_digest and build_run.train_partition_digest:
        if proposed_dataset_digest != build_run.train_partition_digest:
            raise CheckpointError("Resume rejected: Training dataset partition digest has changed.")

    return True
