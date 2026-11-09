"""Data Protection, Masking, and Finding Review API endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset import (
    Dataset,
    DatasetVersion,
    DatasetVersionStatus,
    Document,
    DocumentFileType,
    ExtractionStatus,
)
from app.models.identity import User
from app.models.masking import (
    DecisionType,
    FindingStatus,
    MaskingDecision,
    MaskingProfile,
    MaskingRun,
    MaskingRunStatus,
    PiiFinding,
)
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.masking.schemas import (
    DocumentReviewResponse,
    ManualFindingCreateRequest,
    MaskingDecisionCreateRequest,
    MaskingDecisionResponse,
    MaskingProfileCreateRequest,
    MaskingProfileResponse,
    MaskingRunCreateRequest,
    MaskingRunResponse,
    PiiFindingResponse,
)
from app.modules.masking.services.detection_service import execute_masking_run
from app.modules.masking.services.offset_service import validate_offsets
from app.modules.storage import StorageBucket, get_storage_provider

router = APIRouter(tags=["Data Protection & Masking"])


# ---------------------------------------------------------------------------
# Masking Profiles
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/masking-profiles",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_masking_profile(
    workspace_id: str,
    payload: MaskingProfileCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_MODIFY)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MaskingProfileResponse:
    ws, _, _ = context
    profile = MaskingProfile(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        language=payload.language,
        enabled_entities_json=json.dumps(payload.enabled_entities),
        replacement_strategy=payload.replacement_strategy,
        confidence_threshold=payload.confidence_threshold,
        created_by=current_user.id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return MaskingProfileResponse.model_validate(profile)


@router.get(
    "/workspaces/{workspace_id}/masking-profiles",
    status_code=status.HTTP_200_OK,
)
def list_masking_profiles(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> list[MaskingProfileResponse]:
    ws, _, _ = context
    profiles = (
        db.execute(
            select(MaskingProfile)
            .where(
                (MaskingProfile.workspace_id == ws.id)
                | (
                    (MaskingProfile.organization_id == ws.organization_id)
                    & (MaskingProfile.workspace_id.is_(None))
                )
            )
            .order_by(MaskingProfile.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [MaskingProfileResponse.model_validate(p) for p in profiles]


# ---------------------------------------------------------------------------
# Masking Runs
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/masking-runs",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_masking_run(
    workspace_id: str,
    payload: MaskingRunCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_ANALYZE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MaskingRunResponse:
    ws, _, _ = context
    storage = get_storage_provider()

    # Validate dataset and version
    dataset = db.execute(
        select(Dataset).where(
            Dataset.id == payload.dataset_id,
            Dataset.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found in this workspace.",
        )

    version = db.execute(
        select(DatasetVersion).where(
            DatasetVersion.id == payload.dataset_version_id,
            DatasetVersion.dataset_id == dataset.id,
        )
    ).scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset version not found.",
        )

    if version.status != DatasetVersionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset version must be finalized in READY status before masking.",
        )

    # Create run
    run = MaskingRun(
        workspace_id=ws.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
        source_dataset_digest=version.content_hash or "empty_digest",
        masking_profile_id=payload.masking_profile_id,
        status=MaskingRunStatus.PENDING,
        created_by=current_user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Execute synchronous detection & masking job
    completed_run = execute_masking_run(db=db, masking_run_id=run.id, storage=storage)
    return MaskingRunResponse.model_validate(completed_run)


@router.get(
    "/workspaces/{workspace_id}/masking-runs",
    status_code=status.HTTP_200_OK,
)
def list_masking_runs(
    workspace_id: str,
    dataset_id: str | None = None,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> list[MaskingRunResponse]:
    ws, _, _ = context
    query = select(MaskingRun).where(MaskingRun.workspace_id == ws.id)
    if dataset_id:
        query = query.where(MaskingRun.dataset_id == dataset_id)
    query = query.order_by(MaskingRun.created_at.desc())

    runs = db.execute(query).scalars().all()
    return [MaskingRunResponse.model_validate(r) for r in runs]


@router.get(
    "/workspaces/{workspace_id}/masking-runs/{run_id}",
    status_code=status.HTTP_200_OK,
)
def get_masking_run(
    workspace_id: str,
    run_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> MaskingRunResponse:
    ws, _, _ = context
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Masking run not found.",
        )
    return MaskingRunResponse.model_validate(run)


# ---------------------------------------------------------------------------
# Findings & Review
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/findings",
    status_code=status.HTTP_200_OK,
)
def list_findings(
    workspace_id: str,
    run_id: str,
    document_id: str | None = None,
    entity_type: str | None = None,
    finding_status: FindingStatus | None = None,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_REVIEW)
    ),
    db: Session = Depends(get_db),
) -> list[PiiFindingResponse]:
    ws, _, _ = context
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    query = select(PiiFinding).where(PiiFinding.masking_run_id == run.id)
    if document_id:
        query = query.where(PiiFinding.document_id == document_id)
    if entity_type:
        query = query.where(PiiFinding.entity_type == entity_type)
    if finding_status:
        query = query.where(PiiFinding.status == finding_status)
    query = query.order_by(PiiFinding.document_id, PiiFinding.start_offset)

    findings = db.execute(query).scalars().all()
    return [PiiFindingResponse.model_validate(f) for f in findings]


@router.post(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/findings/manual",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_manual_finding(
    workspace_id: str,
    run_id: str,
    payload: ManualFindingCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_MODIFY)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PiiFindingResponse:
    ws, _, _ = context
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    doc = db.execute(
        select(Document).where(
            Document.id == payload.document_id,
            Document.dataset_version_id == run.dataset_version_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Validate offsets against document length
    if doc.char_count > 0:
        validate_offsets(payload.start_offset, payload.end_offset, doc.char_count)

    finding = PiiFinding(
        masking_run_id=run.id,
        document_id=doc.id,
        entity_type=payload.entity_type,
        recognizer_name="HumanReviewerManual",
        recognizer_version="1.0",
        detection_score=1.0,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        offset_unit="unicode_codepoint",
        page_number=payload.page_number,
        status=FindingStatus.MANUAL,
        is_manual=True,
    )
    db.add(finding)
    run.findings_count += 1
    db.commit()
    db.refresh(finding)
    return PiiFindingResponse.model_validate(finding)


@router.post(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/findings/{finding_id}/decisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def record_finding_decision(
    workspace_id: str,
    run_id: str,
    finding_id: str,
    payload: MaskingDecisionCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_REVIEW)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MaskingDecisionResponse:
    ws, _, _ = context
    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    finding = db.execute(
        select(PiiFinding).where(
            PiiFinding.id == finding_id,
            PiiFinding.masking_run_id == run.id,
        )
    ).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")

    decision = MaskingDecision(
        masking_run_id=run.id,
        finding_id=finding.id,
        reviewer_user_id=current_user.id,
        decision_type=payload.decision_type,
        reason=payload.reason,
        custom_replacement=payload.custom_replacement,
    )
    db.add(decision)

    # Update finding status based on decision
    if payload.decision_type == DecisionType.FALSE_POSITIVE:
        finding.status = FindingStatus.FALSE_POSITIVE
    elif payload.decision_type == DecisionType.CONFIRMED:
        finding.status = FindingStatus.CONFIRMED

    # Recalculate unresolved count
    unresolved = (
        db.execute(
            select(func.count(PiiFinding.id)).where(
                PiiFinding.masking_run_id == run.id,
                PiiFinding.status == FindingStatus.DETECTED,
            )
        ).scalar()
        or 0
    )
    run.unresolved_findings_count = unresolved

    db.commit()
    db.refresh(decision)
    return MaskingDecisionResponse.model_validate(decision)


@router.get(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/documents/{document_id}/review",
    status_code=status.HTTP_200_OK,
)
def get_document_review_content(
    workspace_id: str,
    run_id: str,
    document_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_REVIEW)
    ),
    db: Session = Depends(get_db),
) -> DocumentReviewResponse:
    ws, _, _ = context
    storage = get_storage_provider()

    run = db.execute(
        select(MaskingRun).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    doc = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.dataset_version_id == run.dataset_version_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Read original text from RAW_UPLOADS
    orig_text = ""
    if doc.extracted_text_key:
        try:
            data, _ = storage.get_object(StorageBucket.RAW_UPLOADS, doc.extracted_text_key)
            orig_text = data.decode("utf-8", errors="replace")
        except Exception:
            orig_text = doc.extracted_text_sample or ""
    elif doc.extracted_text_sample:
        orig_text = doc.extracted_text_sample

    # Read masked text from MASKED_DATASETS
    masked_key = f"runs/{run.id}/docs/{doc.id}.masked.txt"
    masked_preview = ""
    try:
        masked_data, _ = storage.get_object(StorageBucket.MASKED_DATASETS, masked_key)
        masked_preview = masked_data.decode("utf-8", errors="replace")
    except Exception:
        masked_preview = ""

    # Fetch findings
    findings = (
        db.execute(
            select(PiiFinding)
            .where(
                PiiFinding.masking_run_id == run.id,
                PiiFinding.document_id == doc.id,
            )
            .order_by(PiiFinding.start_offset)
        )
        .scalars()
        .all()
    )

    requires_ocr = (
        doc.file_type == DocumentFileType.IMAGE
        or (doc.char_count == 0 and doc.file_type == DocumentFileType.PDF)
        or doc.extraction_status == ExtractionStatus.FAILED
    )

    return DocumentReviewResponse(
        document_id=doc.id,
        document_name=doc.name,
        file_type=doc.file_type.value,
        original_text=orig_text,
        masked_preview=masked_preview,
        findings=[PiiFindingResponse.model_validate(f) for f in findings],
        extraction_status=doc.extraction_status.value,
        requires_ocr=requires_ocr,
    )
