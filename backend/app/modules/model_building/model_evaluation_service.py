"""Integration with Milestone 6 Evaluation Engine for pre- and post-quantization quality validation."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationRun, SplitType
from app.models.model_building import (
    ModelBuildRun,
    ModelEvaluationLink,
    ModelRole,
    StagedModelArtifact,
)


class ModelEvaluationIntegrationError(Exception):
    """Raised when evaluation linking violates M6 or M10 integrity rules."""


def link_model_evaluation(
    db: Session,
    build_run: ModelBuildRun,
    staged_artifact: StagedModelArtifact,
    evaluation_run: EvaluationRun,
    model_role: ModelRole,
    base_evaluation_score: float | None = None,
) -> ModelEvaluationLink:
    """Link an evaluated staged model artifact to an M6 EvaluationRun.

    Enforces:
    1. Evaluation split must be DEVELOPMENT or VALIDATION (NEVER HOLDOUT).
    2. Quality delta calculation against base model.
    3. Transparent reporting of regressions.
    """
    # Safety Check: Never allow Holdout split evaluation during model development
    # (Holdout is strictly reserved for authorized Gate-level evaluations)
    if getattr(evaluation_run, "split", None) == SplitType.HOLDOUT:
        raise ModelEvaluationIntegrationError(
            "Protected HOLDOUT split cannot be linked directly to development model builds."
        )

    score = float(evaluation_run.overall_score or 0.0)
    base_score = base_evaluation_score if base_evaluation_score is not None else score
    quality_delta = round(score - base_score, 4)

    comparison_summary = {
        "model_role": model_role.value,
        "evaluation_suite_id": evaluation_run.suite_id,
        "overall_score": score,
        "base_score": base_score,
        "quality_delta": quality_delta,
        "is_regression": quality_delta < 0,
        "latency_p50_ms": getattr(evaluation_run, "latency_p50_ms", None),
    }

    link = ModelEvaluationLink(
        organization_id=build_run.organization_id,
        workspace_id=build_run.workspace_id,
        build_run_id=build_run.id,
        staged_artifact_id=staged_artifact.id,
        evaluation_run_id=evaluation_run.id,
        model_role=model_role,
        evaluation_suite_id=evaluation_run.suite_id,
        evaluation_split="VALIDATION",
        overall_score=score,
        quality_delta=quality_delta,
        latency_delta_ms=0.0,
        memory_delta_mb=0.0,
        comparison_summary_json=json.dumps(comparison_summary),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
