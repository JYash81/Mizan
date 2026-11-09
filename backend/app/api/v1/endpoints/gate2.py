"""Gate 2 Financial Approval API Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.gate2 import Gate2ApprovalStatus
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.gate2.approval_service import Gate2ApprovalError, Gate2ApprovalService
from app.modules.gate2.financial_authorization import FinancialAuthorizationService
from app.modules.gate2.schemas.gate2 import (
    FinancialAuthorizationRequest,
    FinancialAuthorizationResponse,
    Gate2ApprovalEventResponse,
    Gate2ApprovalRequestCreate,
    Gate2ApprovalRequestResponse,
    Gate2DecisionRequest,
    Gate2RevokeRequest,
)

router = APIRouter(tags=["Gate 2 Financial Approval"])
approval_svc = Gate2ApprovalService()
authz_svc = FinancialAuthorizationService(approval_service=approval_svc)


def _serialize_request(req) -> Gate2ApprovalRequestResponse:
    """Helper to convert ORM model with events to response schema."""
    events = [
        Gate2ApprovalEventResponse(
            id=e.id,
            approval_request_id=e.approval_request_id,
            actor_id=e.actor_id,
            event_type=e.event_type,
            previous_status=e.previous_status,
            new_status=e.new_status,
            message=e.message,
            metadata_json=e.metadata_json,
            created_at=e.created_at,
        )
        for e in req.events
    ]
    return Gate2ApprovalRequestResponse(
        id=req.id,
        organization_id=req.organization_id,
        workspace_id=req.workspace_id,
        requester_id=req.requester_id,
        title=req.title,
        purpose=req.purpose,
        workload_type=req.workload_type,
        dataset_id=req.dataset_id,
        dataset_version_id=req.dataset_version_id,
        gate1_approval_id=req.gate1_approval_id,
        experiment_id=req.experiment_id,
        hardware_profile_key=req.hardware_profile_key,
        provider_name=req.provider_name,
        instance_type=req.instance_type,
        region=req.region,
        estimated_duration_hours=req.estimated_duration_hours,
        max_duration_hours=req.max_duration_hours,
        estimated_compute_cost=req.estimated_compute_cost,
        estimated_storage_cost=req.estimated_storage_cost,
        estimated_total_cost=req.estimated_total_cost,
        max_authorized_budget=req.max_authorized_budget,
        currency=req.currency,
        proposal_digest=req.proposal_digest,
        proposal_payload_json=req.proposal_payload_json,
        pricing_snapshot_json=req.pricing_snapshot_json,
        pricing_catalog_version=req.pricing_catalog_version,
        status=req.status,
        approver_id=req.approver_id,
        approver_role_snapshot=req.approver_role_snapshot,
        approval_signature=req.approval_signature,
        signing_key_id=req.signing_key_id,
        signed_payload=req.signed_payload,
        signed_at=req.signed_at,
        decision_reason=req.decision_reason,
        rejection_reason=req.rejection_reason,
        revocation_reason=req.revocation_reason,
        revoked_by_id=req.revoked_by_id,
        revoked_at=req.revoked_at,
        expires_at=req.expires_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        events=events,
    )


@router.post(
    "/workspaces/{workspace_id}/gate2/requests",
    response_model=Gate2ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_gate2_request(
    workspace_id: str,
    payload: Gate2ApprovalRequestCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.GATE2_REQUEST)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Gate2ApprovalRequestResponse:
    """Create a new Gate 2 financial approval request for an infrastructure workload."""
    ws, org_mem, _ = context
    try:
        req = approval_svc.create_request(
            db,
            organization_id=org_mem.organization_id,
            workspace_id=ws.id,
            requester_id=current_user.id,
            data=payload,
        )
    except Gate2ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _serialize_request(req)


@router.get(
    "/workspaces/{workspace_id}/gate2/requests",
    response_model=list[Gate2ApprovalRequestResponse],
)
def list_gate2_requests(
    workspace_id: str,
    status_filter: Gate2ApprovalStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_READ)
    ),
    db: Session = Depends(get_db),
) -> list[Gate2ApprovalRequestResponse]:
    """List Gate 2 financial approval requests in the workspace."""
    ws, _, _ = context
    requests = approval_svc.list_requests(
        db,
        workspace_id=ws.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [_serialize_request(r) for r in requests]


@router.get(
    "/workspaces/{workspace_id}/gate2/requests/{request_id}",
    response_model=Gate2ApprovalRequestResponse,
)
def get_gate2_request(
    workspace_id: str,
    request_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_READ)
    ),
    db: Session = Depends(get_db),
) -> Gate2ApprovalRequestResponse:
    """Get single Gate 2 approval request by ID with full audit events."""
    ws, _, _ = context
    req = approval_svc.get_request(db, request_id=request_id, workspace_id=ws.id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gate 2 approval request '{request_id}' not found.",
        )
    return _serialize_request(req)


@router.post(
    "/workspaces/{workspace_id}/gate2/requests/{request_id}/decide",
    response_model=Gate2ApprovalRequestResponse,
    dependencies=[Depends(require_csrf)],
)
def decide_gate2_request(
    workspace_id: str,
    request_id: str,
    payload: Gate2DecisionRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.GATE2_APPROVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Gate2ApprovalRequestResponse:
    """Approve (with Ed25519 digital signature) or reject a Gate 2 request."""
    ws, org_mem, ws_role = context
    role_snapshot = ws_role.value if ws_role else org_mem.role.value

    try:
        req = approval_svc.decide_request(
            db,
            request_id=request_id,
            workspace_id=ws.id,
            actor_id=current_user.id,
            actor_role=role_snapshot,
            data=payload,
        )
    except Gate2ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _serialize_request(req)


@router.post(
    "/workspaces/{workspace_id}/gate2/requests/{request_id}/revoke",
    response_model=Gate2ApprovalRequestResponse,
    dependencies=[Depends(require_csrf)],
)
def revoke_gate2_request(
    workspace_id: str,
    request_id: str,
    payload: Gate2RevokeRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.GATE2_REVOKE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Gate2ApprovalRequestResponse:
    """Revoke a previously approved Gate 2 request."""
    ws, _, _ = context
    try:
        req = approval_svc.revoke_request(
            db,
            request_id=request_id,
            workspace_id=ws.id,
            actor_id=current_user.id,
            data=payload,
        )
    except Gate2ApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _serialize_request(req)


@router.post(
    "/workspaces/{workspace_id}/gate2/authorize",
    response_model=FinancialAuthorizationResponse,
)
def check_financial_authorization(
    workspace_id: str,
    payload: FinancialAuthorizationRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_READ)
    ),
    db: Session = Depends(get_db),
) -> FinancialAuthorizationResponse:
    """Evaluate whether an approved workload is cryptographically valid and policy-authorized."""
    return authz_svc.authorize_execution(db, req=payload)
