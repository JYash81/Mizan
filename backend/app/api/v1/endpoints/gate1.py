"""Gate 1 Human Approval API Endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.masking import Gate1Approval, MaskingRun
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.masking.approval.gate1_service import (
    Gate1ApprovalError,
    approve_gate1,
    reject_gate1,
    verify_gate1_approval,
)
from app.modules.masking.schemas import (
    Gate1ApprovalRequest,
    Gate1ApprovalResponse,
    Gate1RejectionRequest,
    Gate1VerificationResponse,
)
from app.modules.storage import get_storage_provider

router = APIRouter(tags=["Gate 1 Human Approval"])


@router.post(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/gate1/approve",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def submit_gate1_approval(
    workspace_id: str,
    run_id: str,
    payload: Gate1ApprovalRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_APPROVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Gate1ApprovalResponse:
    ws, org_mem, ws_role = context
    storage = get_storage_provider()

    role_snapshot = ws_role.value if ws_role else org_mem.role.value

    # Verify run exists in workspace (anti-enumeration 404)
    run_exists = db.execute(
        select(MaskingRun.id).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Masking run not found.",
        )

    try:
        approval = approve_gate1(
            db=db,
            workspace_id=ws.id,
            masking_run_id=run_id,
            reviewer_user=current_user,
            reviewer_role_snapshot=role_snapshot,
            decision_reason=payload.decision_reason,
            storage=storage,
            override_coverage_reason=payload.override_coverage_reason,
        )
        return Gate1ApprovalResponse.model_validate(approval)
    except Gate1ApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/workspaces/{workspace_id}/masking-runs/{run_id}/gate1/reject",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def submit_gate1_rejection(
    workspace_id: str,
    run_id: str,
    payload: Gate1RejectionRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_APPROVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Gate1ApprovalResponse:
    ws, org_mem, ws_role = context

    role_snapshot = ws_role.value if ws_role else org_mem.role.value

    run_exists = db.execute(
        select(MaskingRun.id).where(
            MaskingRun.id == run_id,
            MaskingRun.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not run_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Masking run not found.",
        )

    try:
        approval = reject_gate1(
            db=db,
            workspace_id=ws.id,
            masking_run_id=run_id,
            reviewer_user=current_user,
            reviewer_role_snapshot=role_snapshot,
            decision_reason=payload.decision_reason,
        )
        return Gate1ApprovalResponse.model_validate(approval)
    except Gate1ApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/workspaces/{workspace_id}/gate1/approvals",
    status_code=status.HTTP_200_OK,
)
def list_gate1_approvals(
    workspace_id: str,
    dataset_version_id: str | None = None,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> list[Gate1ApprovalResponse]:
    ws, _, _ = context
    query = select(Gate1Approval).where(Gate1Approval.workspace_id == ws.id)
    if dataset_version_id:
        query = query.where(Gate1Approval.dataset_version_id == dataset_version_id)
    query = query.order_by(Gate1Approval.created_at.desc())

    approvals = db.execute(query).scalars().all()
    return [Gate1ApprovalResponse.model_validate(a) for a in approvals]


@router.get(
    "/workspaces/{workspace_id}/gate1/approvals/{approval_id}",
    status_code=status.HTTP_200_OK,
)
def get_gate1_approval(
    workspace_id: str,
    approval_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> Gate1ApprovalResponse:
    ws, _, _ = context
    approval = db.execute(
        select(Gate1Approval).where(
            Gate1Approval.id == approval_id,
            Gate1Approval.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")
    return Gate1ApprovalResponse.model_validate(approval)


@router.post(
    "/workspaces/{workspace_id}/gate1/approvals/{approval_id}/verify",
    status_code=status.HTTP_200_OK,
)
def verify_gate1_attestation(
    workspace_id: str,
    approval_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MASKING_READ)
    ),
    db: Session = Depends(get_db),
) -> Gate1VerificationResponse:
    ws, _, _ = context
    storage = get_storage_provider()

    approval = db.execute(
        select(Gate1Approval).where(
            Gate1Approval.id == approval_id,
            Gate1Approval.workspace_id == ws.id,
        )
    ).scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")

    is_valid = verify_gate1_approval(db=db, approval_id=approval.id, storage=storage)

    message = (
        "Ed25519 digital signature and source dataset integrity verified successfully."
        if is_valid
        else "Verification failed: Attestation signature mismatch, dataset mutation, or rejected status."
    )

    return Gate1VerificationResponse(
        approval_id=approval.id,
        is_valid=is_valid,
        decision=approval.decision.value,
        reviewer_user_id=approval.reviewer_user_id,
        reviewer_role=approval.reviewer_role_snapshot,
        signature_algorithm=approval.signature_algorithm,
        signing_key_id=approval.signing_key_id,
        source_dataset_digest=approval.source_dataset_digest,
        masked_output_digest=approval.masked_output_digest,
        verification_message=message,
        verified_at=datetime.now(UTC),
    )
