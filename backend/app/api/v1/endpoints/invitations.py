"""Organization and workspace invitation endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import (
    Invitation,
    Organization,
    OrganizationMembership,
)
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import (
    require_org_permission,
)
from app.modules.authorization.permissions import OrganizationPermission
from app.modules.workspaces.schemas import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    InvitationResponse,
)
from app.modules.workspaces.services import invitation_service

router = APIRouter(tags=["Invitations"])


@router.post(
    "/organizations/{organization_id}/invitations",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_invitation(
    organization_id: str,
    payload: CreateInvitationRequest,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.MEMBERS_INVITE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        inv, _ = invitation_service.create_invitation(
            db=db,
            organization_id=org.id,
            invited_by_id=current_user.id,
            email=payload.email,
            org_role=payload.organization_role,
            workspace_id=payload.workspace_id,
            ws_role=payload.workspace_role,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    res = InvitationResponse(
        id=inv.id,
        organization_id=inv.organization_id,
        workspace_id=inv.workspace_id,
        invited_email=inv.invited_email,
        organization_role=inv.organization_role.value,
        workspace_role=inv.workspace_role.value if inv.workspace_role else None,
        status=inv.status.value,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
    )
    return {"data": res}


@router.get("/organizations/{organization_id}/invitations")
def list_organization_invitations(
    organization_id: str,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.MEMBERS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    invitations = invitation_service.list_organization_invitations(db, org.id)
    results = [
        InvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            workspace_id=inv.workspace_id,
            invited_email=inv.invited_email,
            organization_role=inv.organization_role.value,
            workspace_role=inv.workspace_role.value if inv.workspace_role else None,
            status=inv.status.value,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]
    return {"data": results}


@router.post("/invitations/accept", dependencies=[Depends(require_csrf)])
def accept_invitation(
    payload: AcceptInvitationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        org_membership, ws_membership = invitation_service.accept_invitation(
            db=db,
            raw_token=payload.token,
            accepting_user_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "data": {
            "organization_id": org_membership.organization_id,
            "organization_role": org_membership.role.value,
            "workspace_id": ws_membership.workspace_id if ws_membership else None,
            "workspace_role": ws_membership.role.value if ws_membership else None,
        }
    }


@router.post("/invitations/reject", dependencies=[Depends(require_csrf)])
def reject_invitation(
    payload: AcceptInvitationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    success = invitation_service.reject_invitation(
        db=db, raw_token=payload.token, user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation token."
        )
    db.commit()
    return {"data": {"message": "Invitation rejected."}}


@router.delete("/invitations/{invitation_id}", dependencies=[Depends(require_csrf)])
def revoke_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    inv = db.get(Invitation, invitation_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")

    # Validate caller has permission in the target organization
    from app.modules.authorization.rbac import has_organization_permission
    from app.modules.workspaces.services.organization_service import get_organization_member

    member = get_organization_member(db, inv.organization_id, current_user.id)
    if member is None or not has_organization_permission(
        member.role, OrganizationPermission.MEMBERS_INVITE
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    invitation_service.revoke_invitation(db, invitation_id, current_user.id)
    db.commit()
    return {"data": {"message": "Invitation revoked."}}
