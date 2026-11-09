"""REST API Endpoints for Mizan Milestone 9: Recommendation Engine & Multi-Objective Optimization."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.models.recommendations import (
    RecommendationCandidate,
    RecommendationRun,
    RecommendationScenario,
)
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.recommendations.objective_registry import (
    ObjectiveDefinition,
    ObjectiveRegistry,
)
from app.modules.recommendations.recommendation_service import RecommendationService
from app.modules.recommendations.schemas.recommendations import (
    CandidateValidationRequest,
    CandidateValidationResult,
    CreateOptimizationProfileRequest,
    CreateRecommendationRunRequest,
    OptimizationProfileResponse,
    RecommendationCandidateResponse,
    RecommendationDecisionResponse,
    RecommendationRunListResponse,
    RecommendationRunResponse,
    RecommendationRunSummaryResponse,
    RecommendationScenarioResponse,
    RecordDecisionRequest,
    UpdateOptimizationProfileRequest,
)
from app.modules.recommendations.weighted_scoring import PREFERENCE_PRESETS

router = APIRouter(tags=["Recommendation Engine & Multi-Objective Optimization"])


def _serialize_candidate(c: RecommendationCandidate) -> RecommendationCandidateResponse:
    exclusion_reasons = []
    if c.exclusion_reasons_json:
        try:
            exclusion_reasons = json.loads(c.exclusion_reasons_json)
        except Exception:
            pass

    dom_by = []
    if c.dominated_by_json:
        try:
            dom_by = json.loads(c.dominated_by_json)
        except Exception:
            pass

    dominates = []
    if c.dominates_json:
        try:
            dominates = json.loads(c.dominates_json)
        except Exception:
            pass

    constraint_results = {}
    if c.constraint_results_json:
        try:
            constraint_results = json.loads(c.constraint_results_json)
        except Exception:
            pass

    evidence_summary = {}
    if c.evidence_summary_json:
        try:
            evidence_summary = json.loads(c.evidence_summary_json)
        except Exception:
            pass

    return RecommendationCandidateResponse(
        id=c.id,
        recommendation_run_id=c.recommendation_run_id,
        experiment_id=c.experiment_id,
        experiment_trial_id=c.experiment_trial_id,
        candidate_label=c.candidate_label,
        configuration_digest=c.configuration_digest,
        evaluation_run_id=c.evaluation_run_id,
        dataset_id=c.dataset_id,
        dataset_version_id=c.dataset_version_id,
        evaluation_suite_id=c.evaluation_suite_id,
        evaluation_suite_version_id=c.evaluation_suite_version_id,
        evaluation_split=c.evaluation_split,
        hardware_profile_key=c.hardware_profile_key,
        provenance_status=c.provenance_status,
        eligibility_status=c.eligibility_status,
        exclusion_reasons=exclusion_reasons,
        objective_values=c.objective_values,
        normalized_objective_values=c.normalized_objective_values,
        constraint_results=constraint_results,
        pareto_frontier_member=c.pareto_frontier_member,
        dominated_by=dom_by,
        dominates=dominates,
        weighted_score=c.weighted_score,
        evidence_summary=evidence_summary,
        explanation_text=c.explanation_text,
        created_at=c.created_at,
    )


def _serialize_scenario(s: RecommendationScenario) -> RecommendationScenarioResponse:
    weight_snapshot = {}
    if s.weight_snapshot_json:
        try:
            weight_snapshot = json.loads(s.weight_snapshot_json)
        except Exception:
            pass

    ranking_snapshot = None
    if s.ranking_snapshot_json:
        try:
            ranking_snapshot = json.loads(s.ranking_snapshot_json)
        except Exception:
            pass

    return RecommendationScenarioResponse(
        id=s.id,
        recommendation_run_id=s.recommendation_run_id,
        scenario_name=s.scenario_name,
        weight_snapshot=weight_snapshot,
        ranking_snapshot=ranking_snapshot,
        explanation=s.explanation,
        created_at=s.created_at,
    )


def _serialize_run(r: RecommendationRun) -> RecommendationRunResponse:
    candidates_resp = [_serialize_candidate(c) for c in r.candidates]
    decisions_resp = [
        RecommendationDecisionResponse(
            id=d.id,
            recommendation_run_id=d.recommendation_run_id,
            selected_candidate_id=d.selected_candidate_id,
            decision=d.decision,
            decision_reason=d.decision_reason,
            actor_id=d.actor_id,
            created_at=d.created_at,
        )
        for d in r.decisions
    ]
    scenarios_resp = [_serialize_scenario(s) for s in r.scenarios]

    return RecommendationRunResponse(
        id=r.id,
        organization_id=r.organization_id,
        workspace_id=r.workspace_id,
        name=r.name,
        description=r.description,
        status=r.status,
        algorithm_version=r.algorithm_version,
        input_digest=r.input_digest,
        result_digest=r.result_digest,
        total_candidates=r.total_candidates,
        eligible_candidates=r.eligible_candidates,
        frontier_candidates=r.frontier_candidates,
        error_summary=r.error_summary,
        created_by=r.created_by,
        created_at=r.created_at,
        completed_at=r.completed_at,
        candidates=candidates_resp,
        decisions=decisions_resp,
        scenarios=scenarios_resp,
    )


# ---------------------------------------------------------------------------
# OBJECTIVE REGISTRY
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/recommendations/objectives",
    response_model=list[ObjectiveDefinition],
)
def list_supported_objectives(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
) -> list[ObjectiveDefinition]:
    """Retrieve all supported optimization objectives, directions, and units."""
    return ObjectiveRegistry.list_objectives()


@router.get(
    "/workspaces/{workspace_id}/recommendations/presets",
    response_model=dict[str, dict[str, float]],
)
def list_preference_presets(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
) -> dict[str, dict[str, float]]:
    """Retrieve predefined transparent preference weight presets."""
    return PREFERENCE_PRESETS


# ---------------------------------------------------------------------------
# CANDIDATE VALIDATION
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/recommendations/validate-candidates",
    response_model=list[CandidateValidationResult],
    dependencies=[Depends(require_csrf)],
)
def validate_candidates(
    workspace_id: str,
    req: CandidateValidationRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[CandidateValidationResult]:
    """Inspect completed trials for a proposed recommendation run."""
    ws, _, _ = context
    return RecommendationService.validate_candidate_trials(
        db=db,
        workspace_id=ws.id,
        experiment_ids=req.experiment_ids,
        trial_ids=req.trial_ids,
    )


# ---------------------------------------------------------------------------
# RECOMMENDATION RUNS
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/recommendations/runs",
    response_model=RecommendationRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_and_execute_recommendation_run(
    workspace_id: str,
    payload: CreateRecommendationRunRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_EXECUTE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RecommendationRunResponse:
    """Create, execute, and persist a multi-objective recommendation run."""
    ws, org_mem, _ = context
    try:
        run = RecommendationService.create_and_execute_recommendation_run(
            db=db,
            workspace_id=ws.id,
            user_id=current_user.id,
            org_id=ws.organization_id,
            req=payload,
        )
        return _serialize_run(run)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/recommendations/runs",
    response_model=RecommendationRunListResponse,
)
def list_recommendation_runs(
    workspace_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
    db: Session = Depends(get_db),
) -> RecommendationRunListResponse:
    """List recommendation runs in the workspace with pagination."""
    ws, _, _ = context
    items, total = RecommendationService.list_recommendation_runs(
        db=db,
        workspace_id=ws.id,
        skip=skip,
        limit=limit,
    )
    summaries = [
        RecommendationRunSummaryResponse(
            id=r.id,
            organization_id=r.organization_id,
            workspace_id=r.workspace_id,
            name=r.name,
            description=r.description,
            status=r.status,
            algorithm_version=r.algorithm_version,
            input_digest=r.input_digest,
            result_digest=r.result_digest,
            total_candidates=r.total_candidates,
            eligible_candidates=r.eligible_candidates,
            frontier_candidates=r.frontier_candidates,
            created_by=r.created_by,
            created_at=r.created_at,
            completed_at=r.completed_at,
        )
        for r in items
    ]
    return RecommendationRunListResponse(items=summaries, total=total)


@router.get(
    "/workspaces/{workspace_id}/recommendations/runs/{run_id}",
    response_model=RecommendationRunResponse,
)
def get_recommendation_run(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
    db: Session = Depends(get_db),
) -> RecommendationRunResponse:
    """Retrieve full recommendation run details including candidates and decisions."""
    ws, _, _ = context
    run = RecommendationService.get_recommendation_run(db, run_id, ws.id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation run '{run_id}' not found.",
        )
    return _serialize_run(run)


@router.post(
    "/workspaces/{workspace_id}/recommendations/runs/{run_id}/decide",
    response_model=RecommendationDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def record_decision(
    workspace_id: str,
    run_id: str,
    payload: RecordDecisionRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_DECIDE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RecommendationDecisionResponse:
    """Record an auditable human review decision on an evaluated candidate or run."""
    ws, _, _ = context
    try:
        decision = RecommendationService.record_decision(
            db=db,
            run_id=run_id,
            workspace_id=ws.id,
            user_id=current_user.id,
            req=payload,
        )
        return RecommendationDecisionResponse(
            id=decision.id,
            recommendation_run_id=decision.recommendation_run_id,
            selected_candidate_id=decision.selected_candidate_id,
            decision=decision.decision,
            decision_reason=decision.decision_reason,
            actor_id=decision.actor_id,
            created_at=decision.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/recommendations/runs/{run_id}/archive",
    response_model=RecommendationRunResponse,
    dependencies=[Depends(require_csrf)],
)
def archive_recommendation_run(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_ARCHIVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RecommendationRunResponse:
    """Archive a recommendation run."""
    ws, _, _ = context
    try:
        run = RecommendationService.archive_recommendation_run(
            db=db,
            run_id=run_id,
            workspace_id=ws.id,
            user_id=current_user.id,
        )
        return _serialize_run(run)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/recommendations/runs/{run_id}/export",
)
def export_recommendation_report(
    workspace_id: str,
    run_id: str,
    format: str = Query("json", pattern="^(json|markdown|md|csv)$"),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_EXPORT)
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Export recommendation run report in JSON, Markdown, or CSV format."""
    ws, _, _ = context
    try:
        content, media_type = RecommendationService.export_report(
            db=db,
            run_id=run_id,
            workspace_id=ws.id,
            format_type=format,
        )
        ext = "md" if format in ("markdown", "md") else format
        filename = f"mizan_recommendation_{run_id[:8]}.{ext}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# OPTIMIZATION PROFILES CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/recommendations/profiles",
    response_model=OptimizationProfileResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_optimization_profile(
    workspace_id: str,
    payload: CreateOptimizationProfileRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_PROFILES_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OptimizationProfileResponse:
    """Create a workspace optimization preference profile."""
    ws, _, _ = context
    profile = RecommendationService.create_optimization_profile(
        db=db,
        workspace_id=ws.id,
        user_id=current_user.id,
        org_id=ws.organization_id,
        req=payload,
    )
    return OptimizationProfileResponse(
        id=profile.id,
        organization_id=profile.organization_id,
        workspace_id=profile.workspace_id,
        name=profile.name,
        description=profile.description,
        objectives=json.loads(profile.objectives_json),
        weights=json.loads(profile.weights_json),
        constraints=json.loads(profile.constraints_json),
        preferred_hardware_profile=profile.preferred_hardware_profile,
        budget_currency=profile.budget_currency,
        version=profile.version,
        created_by=profile.created_by,
        updated_by=profile.updated_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/workspaces/{workspace_id}/recommendations/profiles",
    response_model=list[OptimizationProfileResponse],
)
def list_optimization_profiles(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[OptimizationProfileResponse]:
    """List optimization preference profiles for the workspace."""
    ws, _, _ = context
    profiles = RecommendationService.list_optimization_profiles(db, ws.id)
    return [
        OptimizationProfileResponse(
            id=p.id,
            organization_id=p.organization_id,
            workspace_id=p.workspace_id,
            name=p.name,
            description=p.description,
            objectives=json.loads(p.objectives_json),
            weights=json.loads(p.weights_json),
            constraints=json.loads(p.constraints_json),
            preferred_hardware_profile=p.preferred_hardware_profile,
            budget_currency=p.budget_currency,
            version=p.version,
            created_by=p.created_by,
            updated_by=p.updated_by,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in profiles
    ]


@router.get(
    "/workspaces/{workspace_id}/recommendations/profiles/{profile_id}",
    response_model=OptimizationProfileResponse,
)
def get_optimization_profile(
    workspace_id: str,
    profile_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_READ)
    ),
    db: Session = Depends(get_db),
) -> OptimizationProfileResponse:
    """Retrieve an optimization profile by ID."""
    ws, _, _ = context
    profile = RecommendationService.get_optimization_profile(db, profile_id, ws.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization profile '{profile_id}' not found.",
        )
    return OptimizationProfileResponse(
        id=profile.id,
        organization_id=profile.organization_id,
        workspace_id=profile.workspace_id,
        name=profile.name,
        description=profile.description,
        objectives=json.loads(profile.objectives_json),
        weights=json.loads(profile.weights_json),
        constraints=json.loads(profile.constraints_json),
        preferred_hardware_profile=profile.preferred_hardware_profile,
        budget_currency=profile.budget_currency,
        version=profile.version,
        created_by=profile.created_by,
        updated_by=profile.updated_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put(
    "/workspaces/{workspace_id}/recommendations/profiles/{profile_id}",
    response_model=OptimizationProfileResponse,
    dependencies=[Depends(require_csrf)],
)
def update_optimization_profile(
    workspace_id: str,
    profile_id: str,
    payload: UpdateOptimizationProfileRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_PROFILES_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OptimizationProfileResponse:
    """Update an existing optimization profile."""
    ws, _, _ = context
    try:
        profile = RecommendationService.update_optimization_profile(
            db=db,
            profile_id=profile_id,
            workspace_id=ws.id,
            user_id=current_user.id,
            req=payload,
        )
        return OptimizationProfileResponse(
            id=profile.id,
            organization_id=profile.organization_id,
            workspace_id=profile.workspace_id,
            name=profile.name,
            description=profile.description,
            objectives=json.loads(profile.objectives_json),
            weights=json.loads(profile.weights_json),
            constraints=json.loads(profile.constraints_json),
            preferred_hardware_profile=profile.preferred_hardware_profile,
            budget_currency=profile.budget_currency,
            version=profile.version,
            created_by=profile.created_by,
            updated_by=profile.updated_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/workspaces/{workspace_id}/recommendations/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def delete_optimization_profile(
    workspace_id: str,
    profile_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.RECOMMENDATIONS_PROFILES_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> None:
    """Delete an optimization profile."""
    ws, _, _ = context
    deleted = RecommendationService.delete_optimization_profile(db, profile_id, ws.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization profile '{profile_id}' not found.",
        )
