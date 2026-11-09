"""Execution engine for safe, deterministic local CPU smoke-test training."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.model_building import (
    ArtifactType,
    ExecutionMode,
    ModelBuildEvent,
    ModelBuildRun,
    ModelBuildStatus,
    RecipeType,
)
from app.modules.model_building.artifact_staging_service import stage_model_artifact
from app.modules.model_building.checkpoint_service import record_checkpoint


class TrainingExecutionError(Exception):
    """Raised when training execution violates safety or execution rules."""


def execute_local_smoke_test(
    db: Session,
    build_run: ModelBuildRun,
) -> ModelBuildRun:
    """Execute a deterministic, safe local CPU smoke test.

    Enforces:
    1. Must be ExecutionMode.LOCAL_SMOKE_TEST and RecipeType.SMOKE_TEST.
    2. Model parameter count must not exceed 150M.
    3. Simulates deterministic steps, writes checkpoints, stages adapter artifact.
    4. $0 expenditure, zero cloud calls, zero external compute.
    """
    if build_run.execution_mode != ExecutionMode.LOCAL_SMOKE_TEST:
        raise TrainingExecutionError(
            f"Build run execution mode is '{build_run.execution_mode.value}', only LOCAL_SMOKE_TEST can be executed on local host."
        )

    if build_run.recipe.recipe_type != RecipeType.SMOKE_TEST:
        raise TrainingExecutionError(
            f"Recipe type '{build_run.recipe.recipe_type.value}' cannot be executed locally on CPU-only workstation."
        )

    if build_run.source_model.parameter_count_millions > 150.0:
        raise TrainingExecutionError(
            f"Model size ({build_run.source_model.parameter_count_millions:.0f}M) exceeds safe local smoke test threshold of 150M parameters."
        )

    # Transition to RUNNING
    build_run.status = ModelBuildStatus.RUNNING
    build_run.started_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(
        ModelBuildEvent(
            build_run_id=build_run.id,
            event_type="EXECUTION_STARTED",
            message="Local CPU smoke test started.",
        )
    )
    db.commit()

    try:
        config = build_run.training_config
        max_steps = int(config.get("max_steps", 5))

        # Simulate 2 checkpoints during training
        ckpt1_bytes = f"mizan_checkpoint_step_1:{build_run.manifest_digest}".encode()
        record_checkpoint(
            db=db,
            build_run=build_run,
            checkpoint_number=1,
            step_number=max_steps // 2,
            epoch=0.5,
            metrics={"train_loss": 2.45, "step": max_steps // 2},
            checkpoint_bytes=ckpt1_bytes,
        )

        ckpt2_bytes = f"mizan_checkpoint_step_final:{build_run.manifest_digest}".encode()
        record_checkpoint(
            db=db,
            build_run=build_run,
            checkpoint_number=2,
            step_number=max_steps,
            epoch=1.0,
            metrics={"train_loss": 1.12, "val_loss": 1.18, "step": max_steps},
            checkpoint_bytes=ckpt2_bytes,
        )

        # Stage the simulated trained adapter artifact
        adapter_payload = (
            b"SAFETENSORS_MOCK_HEADER"
            + f":adapter_weights:{build_run.source_model.model_key}:{build_run.source_revision}".encode()
        )
        stage_model_artifact(
            db=db,
            build_run=build_run,
            artifact_type=ArtifactType.LORA_ADAPTER,
            format_name="SAFETENSORS",
            artifact_bytes=adapter_payload,
        )

        # Mark completed
        build_run.status = ModelBuildStatus.COMPLETED
        build_run.completed_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            ModelBuildEvent(
                build_run_id=build_run.id,
                event_type="EXECUTION_COMPLETED",
                message="Local CPU smoke test completed successfully. Adapter artifact staged.",
            )
        )
        db.commit()

    except Exception as exc:
        build_run.status = ModelBuildStatus.FAILED
        build_run.error_summary = str(exc)
        build_run.completed_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            ModelBuildEvent(
                build_run_id=build_run.id,
                event_type="EXECUTION_FAILED",
                message=f"Local CPU smoke test failed: {exc}",
            )
        )
        db.commit()

    db.refresh(build_run)
    return build_run
