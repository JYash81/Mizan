"""REST API endpoints for Mizan Milestone 6: Exam & Evaluation Engine."""

from __future__ import annotations

import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.rag import get_embedding_provider, get_vector_store
from app.db.session import get_db
from app.models.evaluation import (
    EvaluationCase,
    EvaluationRubric,
    EvaluationRun,
    EvaluationSuite,
    EvaluationSuiteStatus,
    GroundTruthStatus,
    ReviewDecision,
    RubricCriterion,
    ScoringMethod,
    SplitType,
)
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.evaluation.repositories.case_repository import CaseRepository
from app.modules.evaluation.repositories.rubric_repository import RubricRepository
from app.modules.evaluation.repositories.run_repository import RunRepository
from app.modules.evaluation.repositories.suite_repository import SuiteRepository
from app.modules.evaluation.schemas.case import (
    EvaluationCaseCreateManual,
    EvaluationCaseResponse,
    EvaluationCaseReviewAction,
)
from app.modules.evaluation.schemas.rubric import (
    EvaluationRubricCreate,
    EvaluationRubricResponse,
    RubricCriterionResponse,
)
from app.modules.evaluation.schemas.run import (
    EvaluationCaseResultResponse,
    EvaluationMetricResultResponse,
    EvaluationRunCreate,
    EvaluationRunResponse,
)
from app.modules.evaluation.schemas.suite import (
    EvaluationSuiteCreate,
    EvaluationSuiteResponse,
    EvaluationSuiteVersionResponse,
    FinalizeSuiteRequest,
    GenerateExamRequest,
)
from app.modules.evaluation.services.evaluation_service import EvaluationService
from app.modules.evaluation.services.generation_service import ExamGenerationService
from app.modules.evaluation.services.report_service import ReportService
from app.modules.evaluation.services.rubric_service import RubricService
from app.modules.rag.providers.registry import get_llm_provider
from app.modules.storage import get_storage_provider

router = APIRouter(tags=["Exam & Evaluation Engine"])


def _serialize_case(c: EvaluationCase) -> EvaluationCaseResponse:
    doc_ids = json.loads(c.source_document_ids_json) if c.source_document_ids_json else []
    chunk_ids = json.loads(c.source_chunk_ids_json) if c.source_chunk_ids_json else []
    return EvaluationCaseResponse(
        id=c.id,
        organization_id=c.organization_id,
        workspace_id=c.workspace_id,
        suite_id=c.suite_id,
        suite_version_id=c.suite_version_id,
        case_type=c.case_type,
        category=c.category,
        difficulty=c.difficulty,
        split=c.split,
        language=c.language,
        question=c.question,
        expected_answer=c.expected_answer,
        is_unanswerable=c.is_unanswerable,
        source_document_ids=doc_ids,
        source_chunk_ids=chunk_ids,
        ground_truth_status=c.ground_truth_status,
        generation_method=c.generation_method,
        reviewer_notes=c.reviewer_notes,
        created_by=c.created_by,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ---------------------------------------------------------------------------
# SUITES
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/evaluation/suites",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-suites",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def create_suite(
    workspace_id: str,
    payload: EvaluationSuiteCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationSuiteResponse:
    """Create a new evaluation suite container in the workspace."""
    ws, _, _ = context
    suite_repo = SuiteRepository()

    slug = payload.slug
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    if not slug:
        slug = f"suite-{uuid.uuid4().hex[:6]}"

    existing = suite_repo.get_suite_by_slug(db, ws.id, slug)
    if existing:
        if payload.slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"EvaluationSuite with slug '{payload.slug}' already exists in workspace.",
            )
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    suite = EvaluationSuite(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        domain=payload.domain,
        language=payload.language,
        source_dataset_id=payload.source_dataset_id,
        source_dataset_version_id=payload.source_dataset_version_id,
        gate1_approval_id=payload.gate1_approval_id,
        created_by=current_user.id,
    )
    suite_repo.create_suite(db, suite)
    db.commit()
    db.refresh(suite)
    resp = EvaluationSuiteResponse.model_validate(suite)
    resp.case_count = 0
    resp.total_cases = 0
    return resp


@router.get(
    "/workspaces/{workspace_id}/evaluation/suites",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-suites",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_suites(
    workspace_id: str,
    skip: int = 0,
    limit: int = 50,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[EvaluationSuiteResponse]:
    """List all evaluation suites for the workspace."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    case_repo = CaseRepository()

    suites = suite_repo.list_suites(db, ws.id, skip=skip, limit=limit)
    responses = []
    for s in suites:
        c_count = case_repo.count_cases_for_suite(db, s.id)
        latest_ver = suite_repo.get_latest_version(db, s.id)
        resp = EvaluationSuiteResponse.model_validate(s)
        resp.case_count = c_count
        resp.total_cases = c_count
        resp.active_version = latest_ver.version_number if latest_ver else None
        responses.append(resp)

    return responses


@router.get(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_suite(
    workspace_id: str,
    suite_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> EvaluationSuiteResponse:
    """Get single evaluation suite by ID."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    case_repo = CaseRepository()

    suite = suite_repo.get_suite(db, ws.id, suite_id)
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationSuite not found.")

    c_count = case_repo.count_cases_for_suite(db, suite.id)
    latest_ver = suite_repo.get_latest_version(db, suite.id)
    resp = EvaluationSuiteResponse.model_validate(suite)
    resp.case_count = c_count
    resp.total_cases = c_count
    resp.active_version = latest_ver.version_number if latest_ver else None
    return resp


@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/generate-cases",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/generate",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}/generate",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def generate_examination(
    workspace_id: str,
    suite_id: str,
    payload: GenerateExamRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Generate examination cases strictly grounded in Gate 1 approved masked documents."""
    ws, _, _ = context
    storage = get_storage_provider()
    gen_service = ExamGenerationService()

    target_count = payload.target_count or payload.target_question_count
    gen_method = payload.generator_type or payload.generation_method

    try:
        cases = gen_service.generate_suite_cases(
            db=db,
            workspace_id=ws.id,
            suite_id=suite_id,
            dataset_version_id=payload.dataset_version_id,
            actor_id=current_user.id,
            storage=storage,
            target_question_count=target_count,
            language=payload.language,
            generation_method=gen_method,
            include_unanswerable=payload.include_unanswerable,
        )
        db.commit()
        serialized = [_serialize_case(c) for c in cases]
        return {
            "suite_id": suite_id,
            "generated_count": len(cases),
            "cases": serialized,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/finalize",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}/finalize",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def finalize_suite(
    workspace_id: str,
    suite_id: str,
    payload: FinalizeSuiteRequest | None = None,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationSuiteVersionResponse:
    """Freeze reviewed examination cases into an immutable, versioned, digest-attested snapshot."""
    ws, _, _ = context
    eval_service = EvaluationService()
    rubric_id = payload.rubric_id if payload else None

    try:
        version = eval_service.finalize_suite_version(
            db=db,
            workspace_id=ws.id,
            suite_id=suite_id,
            actor_id=current_user.id,
            rubric_id=rubric_id,
        )
        db.commit()
        db.refresh(version)
        resp = EvaluationSuiteVersionResponse.model_validate(version)
        resp.version_id = version.id
        return resp
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/versions",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}/versions",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_suite_versions(
    workspace_id: str,
    suite_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[EvaluationSuiteVersionResponse]:
    """List all finalized versions for an evaluation suite."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    suite = suite_repo.get_suite(db, ws.id, suite_id)
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationSuite not found.")

    versions = suite_repo.list_versions(db, suite_id)
    resps = []
    for v in versions:
        r = EvaluationSuiteVersionResponse.model_validate(v)
        r.version_id = v.id
        resps.append(r)
    return resps


# ---------------------------------------------------------------------------
# CASES
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/cases",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}/cases",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_suite_cases(
    workspace_id: str,
    suite_id: str,
    suite_version_id: str | None = None,
    split: SplitType | None = None,
    ground_truth_status: GroundTruthStatus | None = None,
    skip: int = 0,
    limit: int = 100,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[EvaluationCaseResponse]:
    """List examination cases for a suite."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    suite = suite_repo.get_suite(db, ws.id, suite_id)
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationSuite not found.")

    case_repo = CaseRepository()
    cases = case_repo.list_cases_for_suite(
        db,
        suite_id,
        suite_version_id=suite_version_id,
        split=split,
        ground_truth_status=ground_truth_status,
        skip=skip,
        limit=limit,
    )
    return [_serialize_case(c) for c in cases]


@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/manual-cases",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/cases",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-suites/{suite_id}/cases",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def create_manual_case(
    workspace_id: str,
    suite_id: str,
    payload: EvaluationCaseCreateManual,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationCaseResponse:
    """Add a manual, human-verified examination case to a draft suite."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    suite = suite_repo.get_suite(db, ws.id, suite_id)
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationSuite not found.")

    # Invariant: If suite is finalized, reject adding cases to protect immutability
    latest_ver = suite_repo.get_latest_version(db, suite.id)
    if suite.status == EvaluationSuiteStatus.READY and latest_ver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add cases to a finalized evaluation suite. Create a new suite or version.",
        )

    case_repo = CaseRepository()
    case = EvaluationCase(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        suite_id=suite.id,
        case_type="manual",
        category=payload.category,
        difficulty=payload.difficulty,
        split=payload.split,
        language=payload.language,
        question=payload.question,
        expected_answer=payload.expected_answer,
        is_unanswerable=payload.is_unanswerable,
        source_document_ids_json=json.dumps(payload.source_document_ids),
        source_chunk_ids_json=json.dumps(payload.source_chunk_ids),
        ground_truth_status=GroundTruthStatus.HUMAN_VERIFIED,
        generation_method="manual_curation",
        reviewer_notes=payload.reviewer_notes,
        created_by=current_user.id,
    )
    case_repo.create_case(db, case)
    db.commit()
    db.refresh(case)
    return _serialize_case(case)


@router.post(
    "/workspaces/{workspace_id}/evaluation/suites/{suite_id}/cases/{case_id}/review",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation/cases/{case_id}/review",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-cases/{case_id}/review",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def review_case(
    workspace_id: str,
    case_id: str,
    payload: EvaluationCaseReviewAction,
    suite_id: str | None = None,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationCaseResponse:
    """Submit a human review action (Approve, Reject, Edit, Flag) on a candidate examination case."""
    ws, _, _ = context
    case_repo = CaseRepository()
    case = case_repo.get_case(db, case_id, ws.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationCase not found.")

    prev_status = case.ground_truth_status.value

    # Apply decision
    from app.models.evaluation import EvaluationReview

    if payload.decision == ReviewDecision.APPROVED:
        case.ground_truth_status = GroundTruthStatus.HUMAN_VERIFIED
        new_ans = payload.corrected_expected_answer or payload.updated_expected_answer
        if new_ans:
            case.expected_answer = new_ans
    elif payload.decision == ReviewDecision.REJECTED:
        case.ground_truth_status = GroundTruthStatus.REJECTED
    elif payload.decision == ReviewDecision.EDITED:
        case.ground_truth_status = GroundTruthStatus.HUMAN_VERIFIED
        if payload.corrected_question:
            case.question = payload.corrected_question
        new_ans = payload.corrected_expected_answer or payload.updated_expected_answer
        if new_ans:
            case.expected_answer = new_ans
        if payload.corrected_difficulty:
            case.difficulty = payload.corrected_difficulty
        if payload.corrected_category:
            case.category = payload.corrected_category
    elif payload.decision == ReviewDecision.FLAGGED:
        case.ground_truth_status = GroundTruthStatus.NEEDS_REVIEW

    if payload.comments:
        case.reviewer_notes = payload.comments

    # Audit review event
    review = EvaluationReview(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        case_id=case.id,
        reviewer_user_id=current_user.id,
        decision=payload.decision,
        previous_status=prev_status,
        new_status=case.ground_truth_status.value,
        comments=payload.comments,
    )
    case_repo.create_review(db, review)
    db.commit()
    db.refresh(case)

    return _serialize_case(case)


# ---------------------------------------------------------------------------
# RUBRICS
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/evaluation/rubrics",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-rubrics",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_rubrics(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[EvaluationRubricResponse]:
    """List evaluation rubrics for workspace (seeds default if none exist)."""
    ws, _, _ = context
    rubric_service = RubricService()
    rubric_service.get_or_create_default_rubric(db, ws.organization_id, ws.id, current_user.id)
    db.commit()

    rubric_repo = RubricRepository()
    rubrics = rubric_repo.list_rubrics(db, ws.id)
    responses = []
    for r in rubrics:
        crit = rubric_repo.list_criteria(db, r.id)
        r_resp = EvaluationRubricResponse.model_validate(r)
        r_resp.criteria = [
            RubricCriterionResponse(
                id=c.id,
                rubric_id=c.rubric_id,
                criterion_key=c.criterion_key,
                name=c.name,
                description=c.description,
                scoring_method=c.scoring_method,
                maximum_score=c.maximum_score,
                weight=c.weight,
                minimum_acceptable_score=c.minimum_acceptable_score,
                configuration=json.loads(c.configuration_json) if c.configuration_json else {},
                created_at=c.created_at,
            )
            for c in crit
        ]
        responses.append(r_resp)
    return responses


@router.get(
    "/workspaces/{workspace_id}/evaluation/rubrics/default",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-rubrics/default",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_default_rubric(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationRubricResponse:
    """Retrieve or initialize the standard default evaluation rubric."""
    ws, _, _ = context
    rubric_service = RubricService()
    default_r = rubric_service.get_or_create_default_rubric(db, ws.organization_id, ws.id, current_user.id)
    db.commit()

    rubric_repo = RubricRepository()
    crit = rubric_repo.list_criteria(db, default_r.id)
    r_resp = EvaluationRubricResponse.model_validate(default_r)
    r_resp.criteria = [
        RubricCriterionResponse(
            id=c.id,
            rubric_id=c.rubric_id,
            criterion_key=c.criterion_key,
            name=c.name,
            description=c.description,
            scoring_method=c.scoring_method,
            maximum_score=c.maximum_score,
            weight=c.weight,
            minimum_acceptable_score=c.minimum_acceptable_score,
            configuration=json.loads(c.configuration_json) if c.configuration_json else {},
            created_at=c.created_at,
        )
        for c in crit
    ]
    return r_resp


@router.post(
    "/workspaces/{workspace_id}/evaluation/rubrics",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-rubrics",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def create_rubric(
    workspace_id: str,
    payload: EvaluationRubricCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationRubricResponse:
    """Create a customized evaluation rubric with weighted criteria."""
    ws, _, _ = context
    rubric_repo = RubricRepository()

    rubric = EvaluationRubric(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        is_default=payload.is_default,
        created_by=current_user.id,
    )
    rubric_repo.create_rubric(db, rubric)

    method_map = {
        "exact_match": ScoringMethod.EXACT_MATCH,
        "token_f1": ScoringMethod.TOKEN_F1,
        "keyword_coverage": ScoringMethod.KEYWORD_COVERAGE,
        "retrieval": ScoringMethod.RETRIEVAL_METRIC,
        "retrieval_quality": ScoringMethod.RETRIEVAL_METRIC,
        "context_relevance": ScoringMethod.CONTEXT_RELEVANCE,
        "faithfulness": ScoringMethod.FAITHFULNESS,
        "groundedness": ScoringMethod.GROUNDEDNESS,
        "citations": ScoringMethod.CITATION_VERIFICATION,
        "citation_verification": ScoringMethod.CITATION_VERIFICATION,
        "abstention": ScoringMethod.ABSTENTION,
        "appropriate_abstention": ScoringMethod.ABSTENTION,
        "safety": ScoringMethod.SAFETY,
        "compliance": ScoringMethod.COMPLIANCE,
    }

    criteria_entities = []
    for c in payload.criteria:
        crit_key = c.criterion_key or c.metric_name or "metric"
        crit_name = c.name or crit_key.replace("_", " ").title()
        crit_desc = c.description or f"Evaluation criterion for {crit_name}"
        min_score = c.min_acceptable_score if c.min_acceptable_score is not None else c.minimum_acceptable_score
        method = c.scoring_method or method_map.get(crit_key.lower(), ScoringMethod.TOKEN_F1)

        crit = RubricCriterion(
            rubric_id=rubric.id,
            criterion_key=crit_key,
            name=crit_name,
            description=crit_desc,
            scoring_method=method,
            maximum_score=c.maximum_score,
            weight=c.weight,
            minimum_acceptable_score=min_score,
            configuration_json=json.dumps(c.configuration),
        )
        criteria_entities.append(crit)

    rubric_repo.add_criteria(db, criteria_entities)
    db.commit()
    db.refresh(rubric)

    resp = EvaluationRubricResponse.model_validate(rubric)
    resp.criteria = [
        RubricCriterionResponse(
            id=c.id,
            rubric_id=c.rubric_id,
            criterion_key=c.criterion_key,
            name=c.name,
            description=c.description,
            scoring_method=c.scoring_method,
            maximum_score=c.maximum_score,
            weight=c.weight,
            minimum_acceptable_score=c.minimum_acceptable_score,
            configuration=json.loads(c.configuration_json),
            created_at=c.created_at,
        )
        for c in criteria_entities
    ]
    return resp


# ---------------------------------------------------------------------------
# RUNS
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/evaluation/runs",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
@router.post(
    "/workspaces/{workspace_id}/evaluation-runs",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
    dependencies=[Depends(require_csrf)],
)
def create_and_execute_run(
    workspace_id: str,
    payload: EvaluationRunCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> EvaluationRunResponse:
    """Create and immediately execute an evaluation run across an immutable suite version."""
    ws, _, _ = context
    suite_repo = SuiteRepository()
    run_repo = RunRepository()

    # Resolve suite
    suite = suite_repo.get_suite(db, ws.id, payload.suite_id)
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationSuite not found.")

    # Resolve suite version
    version_id = payload.suite_version_id
    if not version_id:
        latest = suite_repo.get_latest_version(db, suite.id)
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Suite has no finalized versions. Finalize the suite first.",
            )
        version_id = latest.id

    version = suite_repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SuiteVersion not found.")

    retrieval_conf = payload.retrieval_config.copy()
    if payload.supplied_responses:
        retrieval_conf["supplied_responses"] = payload.supplied_responses

    run = EvaluationRun(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        suite_id=suite.id,
        suite_version_id=version.id,
        rubric_id=payload.rubric_id or version.rubric_id,
        rubric_version=version.rubric_version,
        target_type=payload.target_type,
        target_name=payload.target_name,
        provider_name=payload.provider_name,
        model_name=payload.model_name,
        retrieval_config_json=json.dumps(retrieval_conf),
        total_cases=version.case_count,
        created_by=current_user.id,
    )
    run_repo.create_run(db, run)

    # Execute run
    v_store = get_vector_store()
    embedder = get_embedding_provider()
    llm = get_llm_provider(payload.provider_name)
    eval_service = EvaluationService()

    completed_run = eval_service.execute_evaluation_run(
        db=db,
        workspace_id=ws.id,
        run_id=run.id,
        vector_store=v_store,
        embedding_provider=embedder,
        llm_provider=llm,
    )
    db.commit()
    db.refresh(completed_run)

    resp = EvaluationRunResponse.model_validate(completed_run)
    breakdown = (
        json.loads(completed_run.score_breakdown_json) if completed_run.score_breakdown_json else {}
    )
    resp.score_breakdown = breakdown
    resp.metric_summary = breakdown
    resp.passed_cases = completed_run.completed_cases
    return resp


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_runs(
    workspace_id: str,
    suite_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[EvaluationRunResponse]:
    """List evaluation runs in workspace."""
    ws, _, _ = context
    run_repo = RunRepository()
    runs = run_repo.list_runs(db, ws.id, suite_id=suite_id, skip=skip, limit=limit)
    resps = []
    for r in runs:
        resp = EvaluationRunResponse.model_validate(r)
        breakdown = json.loads(r.score_breakdown_json) if r.score_breakdown_json else {}
        resp.score_breakdown = breakdown
        resp.metric_summary = breakdown
        resp.passed_cases = r.completed_cases
        resps.append(resp)
    return resps


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs/{run_id}",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs/{run_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_run(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> EvaluationRunResponse:
    """Get single evaluation run details and overall scorecard."""
    ws, _, _ = context
    run_repo = RunRepository()
    run = run_repo.get_run(db, run_id, ws.id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationRun not found.")

    resp = EvaluationRunResponse.model_validate(run)
    breakdown = json.loads(run.score_breakdown_json) if run.score_breakdown_json else {}
    if "appropriate_abstention" in breakdown and "abstention" not in breakdown:
        breakdown["abstention"] = breakdown["appropriate_abstention"]
    resp.score_breakdown = breakdown
    resp.metric_summary = breakdown
    resp.passed_cases = run.completed_cases

    case_results = run_repo.list_case_results(db, run.id)
    c_resps = []
    for cr in case_results:
        metrics = run_repo.list_metric_results_for_case_result(db, cr.id)
        m_resps = [
            EvaluationMetricResultResponse(
                id=m.id,
                case_result_id=m.case_result_id,
                metric_key=m.metric_key,
                raw_score=m.raw_score,
                normalized_score=m.normalized_score,
                score_scale=m.score_scale,
                status=m.status,
                evaluator_version=m.evaluator_version,
                details=json.loads(m.details_json) if m.details_json else {},
                created_at=m.created_at,
            )
            for m in metrics
        ]
        c_resps.append(
            EvaluationCaseResultResponse(
                id=cr.id,
                run_id=cr.run_id,
                case_id=cr.case_id,
                actual_answer=cr.actual_answer,
                actual_answer_digest=cr.actual_answer_digest,
                overall_case_score=cr.overall_case_score,
                status=cr.status,
                retrieved_chunks=json.loads(cr.retrieved_chunks_json) if cr.retrieved_chunks_json else [],
                citations=json.loads(cr.citations_json) if cr.citations_json else [],
                latency_ms=cr.latency_ms,
                created_at=cr.created_at,
                metrics=m_resps,
            )
        )
    resp.case_results = c_resps
    return resp


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs/{run_id}/results",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs/{run_id}/results",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_run_results(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> list[EvaluationCaseResultResponse]:
    """Get per-case results with full metric breakdowns for an evaluation run."""
    ws, _, _ = context
    run_repo = RunRepository()
    run = run_repo.get_run(db, run_id, ws.id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationRun not found.")

    case_results = run_repo.list_case_results(db, run.id)
    responses = []
    for cr in case_results:
        metrics = run_repo.list_metric_results_for_case_result(db, cr.id)
        m_resps = [
            EvaluationMetricResultResponse(
                id=m.id,
                case_result_id=m.case_result_id,
                metric_key=m.metric_key,
                raw_score=m.raw_score,
                normalized_score=m.normalized_score,
                score_scale=m.score_scale,
                status=m.status,
                evaluator_version=m.evaluator_version,
                details=json.loads(m.details_json) if m.details_json else {},
                created_at=m.created_at,
            )
            for m in metrics
        ]
        resp = EvaluationCaseResultResponse(
            id=cr.id,
            run_id=cr.run_id,
            case_id=cr.case_id,
            actual_answer=cr.actual_answer,
            actual_answer_digest=cr.actual_answer_digest,
            overall_case_score=cr.overall_case_score,
            status=cr.status,
            retrieved_chunks=json.loads(cr.retrieved_chunks_json) if cr.retrieved_chunks_json else [],
            citations=json.loads(cr.citations_json) if cr.citations_json else [],
            latency_ms=cr.latency_ms,
            created_at=cr.created_at,
            metrics=m_resps,
        )
        responses.append(resp)
    return responses


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs/{run_id}/report",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs/{run_id}/report",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_report(
    workspace_id: str,
    run_id: str,
    format: str = Query("json", description="Output format: json, markdown, or csv"),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
):
    """Generate structured evaluation report in JSON, Markdown, or CSV format."""
    ws, _, _ = context
    report_service = ReportService()
    try:
        report = report_service.generate_full_report(db, ws.id, run_id)
        if format.lower() == "markdown":
            md = report_service.export_markdown_report(report)
            return Response(content=md, media_type="text/markdown")
        elif format.lower() == "csv":
            csv_data = report_service.export_csv_report(report)
            return Response(content=csv_data, media_type="text/csv")
        return report
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs/{run_id}/report/markdown",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs/{run_id}/report/markdown",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_report_markdown(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Export evaluation report in Markdown format."""
    ws, _, _ = context
    report_service = ReportService()
    try:
        report = report_service.generate_full_report(db, ws.id, run_id)
        md = report_service.export_markdown_report(report)
        return Response(content=md, media_type="text/markdown")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/workspaces/{workspace_id}/evaluation/runs/{run_id}/report/csv",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/workspaces/{workspace_id}/evaluation-runs/{run_id}/report/csv",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_report_csv(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.EXPERIMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> Response:
    """Export per-case evaluation results in CSV format."""
    ws, _, _ = context
    report_service = ReportService()
    try:
        report = report_service.generate_full_report(db, ws.id, run_id)
        csv_data = report_service.export_csv_report(report)
        return Response(content=csv_data, media_type="text/csv")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
