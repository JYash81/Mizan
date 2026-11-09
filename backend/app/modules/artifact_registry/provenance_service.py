"""5-Pillar Comprehensive Provenance Verification Service for Milestone 11.

Evaluates:
1. Base Model License and Access rights.
2. Dataset Data Rights & Gate 1 cryptographic approval.
3. Build Manifest & Checkpoint Provenance.
4. M6/M10 Evaluation Evidence & Quality Regressions.
5. Hardware Feasibility & Inference Resource Requirements.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetVersion
from app.models.evaluation import EvaluationRun, EvaluationRunStatus
from app.models.masking import Gate1Approval, Gate1Decision
from app.models.model_building import (
    ExternalProcessingAuthorization,
    ModelBuildRun,
    ModelBuildStatus,
    ModelSource,
)


def verify_model_provenance(
    db: Session,
    workspace_id: str,
    source_model_key: str,
    source_model_revision: str,
    recipe_key: str,
    build_run_id: str | None = None,
    dataset_id: str | None = None,
    dataset_version_id: str | None = None,
    dataset_version_digest: str | None = None,
    gate1_approval_id: str | None = None,
    evaluation_run_id: str | None = None,
    base_evaluation_score: float | None = None,
    final_evaluation_score: float | None = None,
    min_ram_mb: float = 0.0,
    min_vram_mb: float = 0.0,
    target_hardware_key: str | None = None,
) -> dict[str, Any]:
    """Execute complete 5-pillar provenance verification for a model release candidate.

    Returns:
        Structured dictionary containing boolean is_valid, individual check results,
        warnings, and blocking errors.
    """
    checks: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    blockers: list[str] = []

    # -------------------------------------------------------------------------
    # Pillar 1: Base Model Licensing & Access Rights
    # -------------------------------------------------------------------------
    p1: dict[str, Any] = {"passed": False, "details": {}}
    model_source = (
        db.query(ModelSource)
        .filter(ModelSource.model_key == source_model_key)
        .order_by(ModelSource.created_at.desc())
        .first()
    )
    if model_source:
        p1["details"] = {
            "model_key": model_source.model_key,
            "license_id": model_source.license_id,
            "license_status": model_source.license_status,
            "commercial_use_allowed": model_source.commercial_use_allowed,
            "access_status": model_source.access_status,
            "immutable_revision": model_source.immutable_revision,
        }
        if model_source.license_status == "NON_COMMERCIAL":
            warnings.append(
                f"Source model '{source_model_key}' carries non-commercial license '{model_source.license_id}'. Commercial use restricted."
            )
        p1["passed"] = True
    else:
        # Fallback for custom or direct test models
        p1["details"] = {
            "model_key": source_model_key,
            "revision": source_model_revision,
            "license_status": "CUSTOM_OR_UNTRACKED",
        }
        warnings.append(f"Model source '{source_model_key}' is not in curated catalog; manual license audit advised.")
        p1["passed"] = True

    checks["BASE_MODEL_LICENSE"] = p1

    # -------------------------------------------------------------------------
    # Pillar 2: Dataset Data Rights & Gate 1 Cryptographic Attestation
    # -------------------------------------------------------------------------
    p2: dict[str, Any] = {"passed": False, "details": {}}
    if dataset_id and dataset_version_id:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id).first()
        dsv = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not ds or not dsv:
            blockers.append("Training dataset or dataset version record not found in workspace.")
        else:
            gate1_q = db.query(Gate1Approval).filter(
                Gate1Approval.dataset_id == dataset_id,
                Gate1Approval.dataset_version_id == dataset_version_id,
                Gate1Approval.workspace_id == workspace_id,
            )
            if gate1_approval_id:
                gate1_q = gate1_q.filter(Gate1Approval.id == gate1_approval_id)
            gate1 = gate1_q.order_by(Gate1Approval.created_at.desc()).first()

            if not gate1 or gate1.decision != Gate1Decision.APPROVED:
                blockers.append(
                    f"Dataset version '{dataset_version_id}' has not passed Gate 1 Data Protection approval."
                )
            else:
                p2["details"] = {
                    "dataset_id": ds.id,
                    "dataset_name": ds.name,
                    "version_number": dsv.version_number,
                    "gate1_approval_id": gate1.id,
                    "decision": gate1.decision.value,
                    "reviewed_at": gate1.reviewed_at.isoformat() if gate1.reviewed_at else None,
                    "masked_output_digest": gate1.masked_output_digest,
                }
                # Check digest match if expected digest provided
                if dataset_version_digest and gate1.masked_output_digest != dataset_version_digest:
                    warnings.append("Dataset version content digest differs from Gate 1 approval record.")

                # If external recipe used, check external processing authorization
                if "COLAB" in recipe_key.upper():
                    ext_auth = (
                        db.query(ExternalProcessingAuthorization)
                        .filter(
                            ExternalProcessingAuthorization.workspace_id == workspace_id,
                            ExternalProcessingAuthorization.dataset_id == dataset_id,
                            ExternalProcessingAuthorization.dataset_version_id == dataset_version_id,
                            ExternalProcessingAuthorization.is_revoked == False,  # noqa: E712
                        )
                        .first()
                    )
                    if not ext_auth:
                        warnings.append(
                            "External runtime recipe used without recorded ExternalProcessingAuthorization."
                        )
                    else:
                        p2["details"]["external_authorization_id"] = ext_auth.id

                p2["passed"] = True
    else:
        # Pre-trained or foundational model with no fine-tuning dataset
        p2["details"] = {"dataset": "NONE_BASE_MODEL_ONLY"}
        p2["passed"] = True

    checks["DATASET_GATE1_DATA_RIGHTS"] = p2

    # -------------------------------------------------------------------------
    # Pillar 3: Build Manifest & Checkpoint Provenance
    # -------------------------------------------------------------------------
    p3: dict[str, Any] = {"passed": False, "details": {}}
    if build_run_id:
        build_run = (
            db.query(ModelBuildRun)
            .filter(ModelBuildRun.id == build_run_id, ModelBuildRun.workspace_id == workspace_id)
            .first()
        )
        if not build_run:
            blockers.append(f"Referenced ModelBuildRun '{build_run_id}' not found in workspace.")
        elif build_run.status != ModelBuildStatus.COMPLETED:
            blockers.append(f"ModelBuildRun status is '{build_run.status.value}', expected COMPLETED.")
        else:
            p3["details"] = {
                "build_run_id": build_run.id,
                "manifest_digest": build_run.manifest_digest,
                "execution_mode": build_run.execution_mode.value,
                "recipe_key": build_run.recipe_key,
                "checkpoint_count": len(build_run.checkpoints),
                "staged_artifact_count": len(build_run.staged_artifacts),
            }
            p3["passed"] = True
    else:
        p3["details"] = {"source": "DIRECT_REGISTERED_RECIPE", "recipe_key": recipe_key}
        p3["passed"] = True

    checks["BUILD_MANIFEST_PROVENANCE"] = p3

    # -------------------------------------------------------------------------
    # Pillar 4: M6/M10 Evaluation Evidence & Quality Regressions
    # -------------------------------------------------------------------------
    p4: dict[str, Any] = {"passed": False, "details": {}}
    if evaluation_run_id:
        eval_run = (
            db.query(EvaluationRun)
            .filter(EvaluationRun.id == evaluation_run_id, EvaluationRun.workspace_id == workspace_id)
            .first()
        )
        if not eval_run:
            warnings.append(f"Referenced EvaluationRun '{evaluation_run_id}' not found in workspace.")
        elif eval_run.status != EvaluationRunStatus.COMPLETED:
            warnings.append(f"EvaluationRun status is '{eval_run.status.value}', incomplete evaluation evidence.")
        else:
            p4["details"] = {
                "evaluation_run_id": eval_run.id,
                "overall_score": eval_run.overall_score,
                "target_name": eval_run.target_name,
                "completed_cases": eval_run.completed_cases,
            }
            p4["passed"] = True

    # Quality score delta assessment
    delta = None
    if base_evaluation_score is not None and final_evaluation_score is not None:
        delta = round(final_evaluation_score - base_evaluation_score, 4)
        p4["details"]["base_score"] = base_evaluation_score
        p4["details"]["final_score"] = final_evaluation_score
        p4["details"]["quality_delta"] = delta
        if delta < -0.01:
            warnings.append(
                f"Quality regression detected: Final evaluation score ({final_evaluation_score:.2f}) dropped by {abs(delta):.2f} relative to base ({base_evaluation_score:.2f})."
            )
        p4["passed"] = True
    elif not evaluation_run_id:
        warnings.append("No benchmark evaluation run linked to this release version. Evaluation evidence missing.")
        p4["passed"] = True  # Non-blocking advisory

    checks["EVALUATION_EVIDENCE"] = p4

    # -------------------------------------------------------------------------
    # Pillar 5: Hardware Feasibility & Inference Resource Requirements
    # -------------------------------------------------------------------------
    p5: dict[str, Any] = {
        "passed": True,
        "details": {
            "min_ram_mb": min_ram_mb,
            "min_vram_mb": min_vram_mb,
            "target_hardware_key": target_hardware_key or "UNSPECIFIED",
        },
    }
    if min_ram_mb > 32768.0 and not min_vram_mb:
        warnings.append(f"High system RAM requirement ({min_ram_mb / 1024:.1f} GB) estimated for CPU inference.")
    checks["HARDWARE_FEASIBILITY"] = p5

    is_valid = len(blockers) == 0

    return {
        "is_valid": is_valid,
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
        "quality_delta": delta,
    }
