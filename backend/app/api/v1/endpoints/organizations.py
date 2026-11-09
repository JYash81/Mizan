"""Organization and organization membership endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import Organization, OrganizationMembership
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import (
    get_current_organization,
    require_org_permission,
)
from app.modules.authorization.permissions import OrganizationPermission
from app.modules.workspaces.schemas import (
    CreateOrganizationRequest,
    OrganizationMemberResponse,
    OrganizationResponse,
    TransferOwnershipRequest,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from app.modules.workspaces.services import organization_service

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_organization(
    payload: CreateOrganizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        org, membership = organization_service.create_organization(
            db=db,
            creator_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    res = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        status=org.status.value,
        created_at=org.created_at,
        role=membership.role.value,
    )
    return {"data": res}


@router.get("/")
def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user_orgs = organization_service.list_user_organizations(db, current_user.id)
    results = [
        OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            status=org.status.value,
            created_at=org.created_at,
            role=membership.role.value,
        )
        for org, membership in user_orgs
    ]
    return {"data": results}


@router.get("/{organization_id}")
def get_organization_detail(
    context: tuple[Organization, OrganizationMembership] = Depends(get_current_organization),
) -> dict[str, Any]:
    org, membership = context
    res = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        status=org.status.value,
        created_at=org.created_at,
        role=membership.role.value,
    )
    return {"data": res}


@router.patch("/{organization_id}", dependencies=[Depends(require_csrf)])
def update_organization(
    payload: UpdateOrganizationRequest,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.UPDATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, membership = context
    try:
        updated = organization_service.update_organization(
            db=db,
            organization_id=org.id,
            actor_id=current_user.id,
            name=payload.name,
            description=payload.description,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    res = OrganizationResponse(
        id=updated.id,
        name=updated.name,
        slug=updated.slug,
        description=updated.description,
        status=updated.status.value,
        created_at=updated.created_at,
        role=membership.role.value,
    )
    return {"data": res}


@router.post("/{organization_id}/archive", dependencies=[Depends(require_csrf)])
def archive_organization(
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.ARCHIVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        organization_service.archive_organization(db, org.id, current_user.id)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"message": f"Organization '{org.name}' has been archived."}}


@router.get("/{organization_id}/members")
def list_organization_members(
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.MEMBERS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    members = organization_service.list_organization_members(db, org.id)
    results = [
        OrganizationMemberResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=membership.role.value,
            membership_status=membership.membership_status.value,
            created_at=membership.created_at,
        )
        for membership, user in members
    ]
    return {"data": results}


@router.patch("/{organization_id}/members/{user_id}", dependencies=[Depends(require_csrf)])
def update_member_role(
    user_id: str,
    payload: UpdateMemberRoleRequest,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.MEMBERS_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        updated = organization_service.update_organization_member_role(
            db=db,
            organization_id=org.id,
            target_user_id=user_id,
            new_role=payload.role,
            actor_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"user_id": updated.user_id, "role": updated.role.value}}


@router.delete("/{organization_id}/members/{user_id}", dependencies=[Depends(require_csrf)])
def remove_member(
    user_id: str,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.MEMBERS_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        organization_service.remove_organization_member(
            db=db,
            organization_id=org.id,
            target_user_id=user_id,
            actor_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"message": "Member removed from organization."}}


@router.post("/{organization_id}/transfer-ownership", dependencies=[Depends(require_csrf)])
def transfer_ownership(
    payload: TransferOwnershipRequest,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.OWNER_TRANSFER)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        organization_service.transfer_organization_ownership(
            db=db,
            organization_id=org.id,
            current_owner_id=current_user.id,
            new_owner_id=payload.new_owner_id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"message": "Organization ownership transferred successfully."}}
