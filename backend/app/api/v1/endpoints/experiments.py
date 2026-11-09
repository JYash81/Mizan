"""REST API Endpoints for Mizan Milestone 7: Experiment Orchestration & Trial Matrix Engine."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evaluation import SplitType
from app.models.experiment import (
    Experiment,
    ExperimentEvent,
    ExperimentStatus,
    ExperimentTrial,
    TrialStatus,
)
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.experiments.digest import compute_canonical_config_digest
from app.modules.experiments.matrix.generator import TrialMatrixGenerator
from app.modules.experiments.matrix.validator import validate_trial_matrix
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository
from app.modules.experiments.schemas.comparison import ExperimentComparisonResponse
from app.modules.experiments.schemas.experiment import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
    MatrixGenerateRequest,
)
from app.modules.experiments.schemas.trial import ExperimentTrialResponse
from app.modules.experiments.services.comparison_service import ExperimentComparisonService
from app.modules.experiments.services.execution_service import ExperimentExecutionService
from app.modules.experiments.services.report_service import ExperimentReportService
from app.modules.masking.approval.gate1_service import require_gate1_approval
from app.modules.storage import get_storage_provider

router = APIRouter(tags=["Model Experimentation & Trial Matrix Engine"])


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or f"exp-{uuid.uuid4().hex[:8]}"


def _serialize_trial(t: ExperimentTrial) -> ExperimentTrialResponse:
    score_bd: dict[str, float] = {}
    if t.score_breakdown_json:
        try:
            score_bd = json.loads(t.score_breakdown_json)
        except Exception:
            pass

    return ExperimentTrialResponse(
        id=t.id,
        organization_id=t.organization_id,
        workspace_id=t.workspace_id,
        experiment_id=t.experiment_id,
        trial_number=t.trial_number,
        name=t.name,
        status=t.status,
        configuration_json=t.configuration_json,
        configuration_digest=t.configuration_digest,
        evaluation_run_id=t.evaluation_run_id,
        aggregate_score=t.aggregate_score,
        score_breakdown=score_bd,
        latency_p50_ms=t.latency_p50_ms,
        latency_p95_ms=t.latency_p95_ms,
        latency_p99_ms=t.latency_p99_ms,
        execution_duration_ms=t.execution_duration_ms,
        error_code=t.error_code,
        error_summary=t.error_summary,
        retry_count=t.retry_count,
        queued_at=t.queued_at,
        started_at=t.started_at,
        completed_at=t.completed_at,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _serialize_experiment(
    exp: Experiment, trials: list[ExperimentTrial] | None = None
) -> ExperimentResponse:
    baseline_dict: dict[str, Any] = {}
    if exp.baseline_config_json:
        try:
            baseline_dict = json.loads(exp.baseline_config_json)
        except Exception:
            pass

    trial_responses = [_serialize_trial(t) for t in trials] if trials is not None else []
    return ExperimentResponse(
        id=exp.id,
        organization_id=exp.organization_id,
        workspace_id=exp.workspace_id,
        name=exp.name,
        slug=exp.slug,
        description=exp.description,
        status=exp.status,
        dataset_id=exp.dataset_id,
        dataset_version_id=exp.dataset_version_id,
        gate1_approval_id=exp.gate1_approval_id,
        dataset_digest=exp.dataset_digest,
        evaluation_suite_id=exp.evaluation_suite_id,
        evaluation_suite_version_id=exp.evaluation_suite_version_id,
        canonical_suite_digest=exp.canonical_suite_digest,
        evaluation_split=exp.evaluation_split,
        baseline_config=baseline_dict,
        configuration_digest=exp.configuration_digest,
        total_trials=exp.total_trials,
        completed_trials=exp.completed_trials,
        failed_trials=exp.failed_trials,
        cancelled_trials=exp.cancelled_trials,
        started_at=exp.started_at,
        completed_at=exp.completed_at,
        cancellation_requested_at=exp.cancellation_requested_at,
        error_message=exp.error_message,
        created_by=exp.created_by,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        trials=trial_responses,
    )


# ---------------------------------------------------------------------------
# EXPERIMENT CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/experiments",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_experiment(
    workspace_id: str,
    payload: ExperimentCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Create a new experiment linked to an approved dataset version and frozen evaluation suite."""
    ws, _, _ = context
    storage = get_storage_provider()
    repo = ExperimentRepository()
    suite_repo = SuiteRepository()

    # 1. Enforce Gate 1 approval (fail-closed)
    approval = require_gate1_approval(
        db=db,
        workspace_id=ws.id,
        dataset_version_id=payload.dataset_version_id,
        storage=storage,
    )

    # 2. Verify frozen suite version
    suite = suite_repo.get_suite(db, ws.id, payload.evaluation_suite_id)
    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EvaluationSuite {payload.evaluation_suite_id} not found in workspace.",
        )

    suite_ver = suite_repo.get_version(db, payload.evaluation_suite_version_id)
    if not suite_ver or suite_ver.suite_id != suite.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"EvaluationSuiteVersion {payload.evaluation_suite_version_id} does not belong to suite {suite.id}.",
        )

    # 3. Check Holdout split protection
    if payload.evaluation_split == SplitType.HOLDOUT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The holdout split is reserved strictly for final un-tuned verification and cannot be used for experiments.",
        )

    # 4. Generate unique slug
    base_slug = payload.slug or _slugify(payload.name)
    slug = base_slug
    idx = 1
    while repo.get_experiment_by_slug(db, ws.id, slug) is not None:
        slug = f"{base_slug}-{idx}"
        idx += 1

    baseline_dict = payload.baseline_config.model_dump()
    baseline_digest = compute_canonical_config_digest(baseline_dict)

    experiment = Experiment(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        status=ExperimentStatus.DRAFT,
        dataset_id=payload.dataset_id,
        dataset_version_id=payload.dataset_version_id,
        gate1_approval_id=approval.id,
        dataset_digest=approval.masked_output_digest,
        evaluation_suite_id=payload.evaluation_suite_id,
        evaluation_suite_version_id=suite_ver.id,
        canonical_suite_digest=suite_ver.suite_digest,
        evaluation_split=payload.evaluation_split,
        baseline_config_json=json.dumps(baseline_dict),
        configuration_digest=baseline_digest,
        total_trials=0,
        completed_trials=0,
        failed_trials=0,
        cancelled_trials=0,
        created_by=current_user.id,
    )
    repo.create_experiment(db, experiment)

    # Audit event
    event = ExperimentEvent(
        experiment_id=experiment.id,
        event_type="EXPERIMENT_CREATED",
        previous_status=None,
        new_status=ExperimentStatus.DRAFT.value,
        metadata_json=json.dumps({"message": f"Experiment '{experiment.name}' created in DRAFT status."}),
        actor_id=current_user.id,
    )
    repo.record_event(db, event)
    db.commit()
    db.refresh(experiment)

    return _serialize_experiment(experiment, [])


@router.get(
    "/workspaces/{workspace_id}/experiments",
    status_code=status.HTTP_200_OK,
)
def list_experiments(
    workspace_id: str,
    status_filter: ExperimentStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[ExperimentResponse]:
    """List experiments in the workspace."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exps = repo.list_experiments(db, ws.id, skip=skip, limit=limit)
    if status_filter:
        exps = [e for e in exps if e.status == status_filter]
    return [_serialize_experiment(e) for e in exps]


@router.get(
    "/workspaces/{workspace_id}/experiments/{experiment_id}",
    status_code=status.HTTP_200_OK,
)
def get_experiment(
    workspace_id: str,
    experiment_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Retrieve full experiment details and its trial matrix."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )
    trials = repo.list_trials(db, exp.id)
    return _serialize_experiment(exp, trials)


@router.patch(
    "/workspaces/{workspace_id}/experiments/{experiment_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def update_experiment(
    workspace_id: str,
    experiment_id: str,
    payload: ExperimentUpdate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Update metadata for an experiment."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )
    if payload.name is not None:
        exp.name = payload.name
    if payload.description is not None:
        exp.description = payload.description
    repo.update_experiment(db, exp)
    db.commit()
    db.refresh(exp)
    trials = repo.list_trials(db, exp.id)
    return _serialize_experiment(exp, trials)


# ---------------------------------------------------------------------------
# TRIAL MATRIX OPERATIONS
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/matrix",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def generate_matrix(
    workspace_id: str,
    experiment_id: str,
    payload: MatrixGenerateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Generate or update the bounded trial matrix (3-9 unique trials) for an experiment."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )

    if exp.status not in {ExperimentStatus.DRAFT, ExperimentStatus.VALIDATING, ExperimentStatus.READY}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot regenerate trial matrix in status '{exp.status.value}'.",
        )

    baseline_dict = json.loads(exp.baseline_config_json) if exp.baseline_config_json else {}

    try:
        generator = TrialMatrixGenerator()
        trial_configs = generator.generate(
            strategy=payload.strategy.value,
            baseline_config=baseline_dict,
            preset_name=payload.preset_name,
            variations=payload.variations,
            manual_trials=payload.manual_trials,
        )
        validate_trial_matrix(trial_configs)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Delete existing trials and insert new bounded trials
    repo.delete_trials(db, exp.id)

    trials_to_add: list[ExperimentTrial] = []
    for i, cfg in enumerate(trial_configs, start=1):
        cfg_dict = cfg if isinstance(cfg, dict) else cfg.model_dump()
        digest = compute_canonical_config_digest(cfg_dict)
        t = ExperimentTrial(
            organization_id=ws.organization_id,
            workspace_id=ws.id,
            experiment_id=exp.id,
            trial_number=i,
            name=cfg_dict.get("_trial_name", f"Trial {i}"),
            status=TrialStatus.PENDING,
            configuration_json=json.dumps(cfg_dict),
            configuration_digest=digest,
        )
        trials_to_add.append(t)

    repo.add_trials(db, trials_to_add)

    exp.total_trials = len(trials_to_add)
    exp.completed_trials = 0
    exp.failed_trials = 0
    exp.cancelled_trials = 0
    exp.status = ExperimentStatus.READY

    event = ExperimentEvent(
        experiment_id=exp.id,
        event_type="MATRIX_GENERATED",
        previous_status=exp.status.value,
        new_status=ExperimentStatus.READY.value,
        metadata_json=json.dumps({"message": f"Generated {len(trials_to_add)} unique trials via {payload.strategy.value}."}),
        actor_id=current_user.id,
    )
    repo.record_event(db, event)
    db.commit()
    db.refresh(exp)

    loaded_trials = repo.list_trials(db, exp.id)
    return _serialize_experiment(exp, loaded_trials)


@router.post(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/validate",
    status_code=status.HTTP_200_OK,
)
def validate_matrix(
    workspace_id: str,
    experiment_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Validate current trial matrix against all Milestone 7 invariants."""
    ws, _, _ = context
    repo = ExperimentRepository()
    storage = get_storage_provider()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )

    # Gate 1 check
    require_gate1_approval(
        db=db,
        workspace_id=ws.id,
        dataset_version_id=exp.dataset_version_id,
        storage=storage,
    )

    trials = repo.list_trials(db, exp.id)
    configs = [t.configuration for t in trials]
    validate_trial_matrix(configs)

    return {
        "valid": True,
        "experiment_id": exp.id,
        "total_trials": len(trials),
        "status": exp.status.value,
        "gate1_approved": True,
        "digest_unique": True,
    }


# ---------------------------------------------------------------------------
# EXECUTION & CANCELLATION
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/execute",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def execute_experiment(
    workspace_id: str,
    experiment_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Trigger sequential execution (local CPU, concurrency: 1) of all trials in the experiment."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )

    exec_service = ExperimentExecutionService()

    try:
        completed_exp = exec_service.execute_experiment(
            db=db,
            workspace_id=ws.id,
            experiment_id=experiment_id,
            actor_id=current_user.id,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    trials = repo.list_trials(db, completed_exp.id)
    return _serialize_experiment(completed_exp, trials)


@router.post(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/cancel",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def cancel_experiment(
    workspace_id: str,
    experiment_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Request cancellation of a running, queued, or ready experiment."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )

    exec_service = ExperimentExecutionService()

    try:
        cancelled_exp = exec_service.request_cancellation(
            db=db,
            workspace_id=ws.id,
            experiment_id=experiment_id,
            actor_id=current_user.id,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    trials = repo.list_trials(db, cancelled_exp.id)
    return _serialize_experiment(cancelled_exp, trials)


# ---------------------------------------------------------------------------
# COMPARISON & REPORTING
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/comparison",
    status_code=status.HTTP_200_OK,
)
def get_comparison(
    workspace_id: str,
    experiment_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> ExperimentComparisonResponse:
    """Retrieve multi-trial factual comparison data across completed trials."""
    ws, _, _ = context
    repo = ExperimentRepository()
    exp = repo.get_experiment(db, experiment_id, ws.id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found in workspace.",
        )

    comparison_service = ExperimentComparisonService()

    try:
        return comparison_service.generate_comparison(
            db=db,
            workspace_id=ws.id,
            experiment_id=experiment_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/trials/{trial_id}",
    status_code=status.HTTP_200_OK,
)
def get_trial(
    workspace_id: str,
    experiment_id: str,
    trial_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> ExperimentTrialResponse:
    """Retrieve detailed trial status and measured results."""
    ws, _, _ = context
    repo = ExperimentRepository()
    trial = repo.get_trial(db, trial_id, experiment_id)
    if not trial or trial.workspace_id != ws.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trial {trial_id} not found in experiment.",
        )
    return _serialize_trial(trial)


@router.get(
    "/workspaces/{workspace_id}/experiments/{experiment_id}/export",
    status_code=status.HTTP_200_OK,
)
def export_report(
    workspace_id: str,
    experiment_id: str,
    format: str = Query("json", pattern="^(json|markdown|csv)$"),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Export comparison report as JSON, Markdown, or CSV."""
    ws, _, _ = context
    comparison_service = ExperimentComparisonService()
    report_service = ExperimentReportService()

    try:
        comp = comparison_service.generate_comparison(
            db=db,
            workspace_id=ws.id,
            experiment_id=experiment_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if format == "json":
        return Response(
            content=report_service.export_json(comp),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=experiment-{experiment_id}.json"},
        )
    elif format == "markdown":
        return Response(
            content=report_service.export_markdown(comp),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=experiment-{experiment_id}.md"},
        )
    else:  # csv
        return Response(
            content=report_service.export_csv(comp),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=experiment-{experiment_id}.csv"},
        )
