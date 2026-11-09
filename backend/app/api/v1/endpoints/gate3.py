"""REST API endpoints for Milestone 11 Gate 3 Human Release Approval & Ed25519 Attestation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.artifact_registry import (
    Gate3Approval,
    Gate3Decision,
)
from app.models.identity import User
from app.models.organization import Workspace, WorkspaceMembership, WorkspaceRole
from app.modules.artifact_registry.exceptions import ArtifactRegistryError
from app.modules.artifact_registry.gate3_service import (
    revoke_model_release,
    submit_gate3_decision,
    verify_gate3_attestation,
)
from app.modules.artifact_registry.schemas import (
    Gate3ApprovalResponse,
    Gate3DecisionRequest,
    Gate3RevocationResponse,
    Gate3RevokeRequest,
    Gate3SignatureVerifyResponse,
)
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission

router = APIRouter(tags=["Gate 3 Human Release Approvals"])


def _verify_workspace_access(db: Session, workspace_id: str) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


def _get_user_workspace_role(db: Session, workspace_id: str, user_id: str) -> WorkspaceRole:
    membership = (
        db.query(WorkspaceMembership)
        .filter(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        # Fallback to WORKSPACE_OWNER if creator/owner
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if ws and ws.created_by == user_id:
            return WorkspaceRole.WORKSPACE_OWNER
        return WorkspaceRole.WORKSPACE_VIEWER
    return membership.role


@router.get(
    "/workspaces/{workspace_id}/gate3/approvals",
    response_model=list[Gate3ApprovalResponse],
    dependencies=[Depends(require_ws_permission(WorkspacePermission.GATE3_READ))],
)
def list_gate3_approvals_endpoint(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Gate3ApprovalResponse]:
    _verify_workspace_access(db, workspace_id)
    approvals = (
        db.query(Gate3Approval)
        .filter(Gate3Approval.workspace_id == workspace_id)
        .order_by(Gate3Approval.reviewed_at.desc())
        .all()
    )
    return [Gate3ApprovalResponse.model_validate(a) for a in approvals]


@router.get(
    "/workspaces/{workspace_id}/gate3/approvals/{version_id}",
    response_model=Gate3ApprovalResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.GATE3_READ))],
)
def get_gate3_approval_endpoint(
    workspace_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Gate3ApprovalResponse:
    _verify_workspace_access(db, workspace_id)
    approval = (
        db.query(Gate3Approval)
        .filter(
            Gate3Approval.workspace_id == workspace_id,
            Gate3Approval.model_version_id == version_id,
        )
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate 3 approval record not found.")
    return Gate3ApprovalResponse.model_validate(approval)


@router.post(
    "/workspaces/{workspace_id}/gate3/approvals/{version_id}/decide",
    response_model=Gate3ApprovalResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.GATE3_APPROVE)),
    ],
)
def submit_gate3_decision_endpoint(
    workspace_id: str,
    version_id: str,
    payload: Gate3DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Gate3ApprovalResponse:
    _verify_workspace_access(db, workspace_id)
    role = _get_user_workspace_role(db, workspace_id, current_user.id)
    try:
        decision_enum = Gate3Decision(payload.decision)
        approval = submit_gate3_decision(
            db=db,
            workspace_id=workspace_id,
            model_version_id=version_id,
            reviewer_user=current_user,
            reviewer_role=role,
            decision=decision_enum,
            decision_reason=payload.decision_reason,
            enforce_separation_of_duties=payload.enforce_separation_of_duties,
            signing_key_id=payload.signing_key_id,
        )
        return Gate3ApprovalResponse.model_validate(approval)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/workspaces/{workspace_id}/gate3/approvals/{version_id}/revoke",
    response_model=Gate3RevocationResponse,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.GATE3_REVOKE)),
    ],
)
def revoke_release_endpoint(
    workspace_id: str,
    version_id: str,
    payload: Gate3RevokeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Gate3RevocationResponse:
    _verify_workspace_access(db, workspace_id)
    role = _get_user_workspace_role(db, workspace_id, current_user.id)
    try:
        revocation = revoke_model_release(
            db=db,
            workspace_id=workspace_id,
            model_version_id=version_id,
            revoking_user=current_user,
            revoking_role=role,
            revocation_reason=payload.revocation_reason,
        )
        return Gate3RevocationResponse.model_validate(revocation)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/workspaces/{workspace_id}/gate3/approvals/{version_id}/verify-signature",
    response_model=Gate3SignatureVerifyResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.GATE3_READ))],
)
def verify_gate3_signature_endpoint(
    workspace_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Gate3SignatureVerifyResponse:
    _verify_workspace_access(db, workspace_id)
    approval = (
        db.query(Gate3Approval)
        .filter(
            Gate3Approval.workspace_id == workspace_id,
            Gate3Approval.model_version_id == version_id,
        )
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate 3 approval record not found.")

    try:
        is_valid = verify_gate3_attestation(
            canonical_payload_json=approval.canonical_payload,
            signature_hex=approval.approval_signature,
            key_id=approval.signing_key_id,
        )
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return Gate3SignatureVerifyResponse(
        is_valid=is_valid,
        signing_key_id=approval.signing_key_id,
        signature_purpose=approval.signature_purpose,
        decision=approval.decision.value,
        reviewed_at=approval.reviewed_at.isoformat(),
        release_manifest_digest=approval.release_manifest_digest,
    )
