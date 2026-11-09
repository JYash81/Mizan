"""Workspace and workspace membership endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    Workspace,
    WorkspaceRole,
)
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import (
    get_current_organization,
    require_org_permission,
    require_ws_permission,
)
from app.modules.authorization.permissions import OrganizationPermission, WorkspacePermission
from app.modules.workspaces.schemas import (
    AddWorkspaceMemberRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceMemberRoleRequest,
    UpdateWorkspaceRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from app.modules.workspaces.services import workspace_service

router = APIRouter(tags=["Workspaces"])


# Organization-scoped workspace routes
@router.post(
    "/organizations/{organization_id}/workspaces",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_workspace(
    organization_id: str,
    payload: CreateWorkspaceRequest,
    context: tuple[Organization, OrganizationMembership] = Depends(
        require_org_permission(OrganizationPermission.WORKSPACES_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    try:
        ws, membership = workspace_service.create_workspace(
            db=db,
            organization_id=org.id,
            creator_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    res = WorkspaceResponse(
        id=ws.id,
        organization_id=ws.organization_id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        status=ws.status.value,
        created_at=ws.created_at,
        role=membership.role.value,
    )
    return {"data": res}


@router.get("/organizations/{organization_id}/workspaces")
def list_organization_workspaces(
    organization_id: str,
    context: tuple[Organization, OrganizationMembership] = Depends(get_current_organization),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org, _ = context
    workspaces = workspace_service.list_organization_workspaces(
        db=db, organization_id=org.id, user_id=current_user.id
    )
    results = [
        WorkspaceResponse(
            id=ws.id,
            organization_id=ws.organization_id,
            name=ws.name,
            slug=ws.slug,
            description=ws.description,
            status=ws.status.value,
            created_at=ws.created_at,
            role=role.value if role else None,
        )
        for ws, role in workspaces
    ]
    return {"data": results}


# Direct workspace-scoped routes
@router.get("/workspaces/{workspace_id}")
def get_workspace_detail(
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.READ)
    ),
) -> dict[str, Any]:
    ws, _, role = context
    res = WorkspaceResponse(
        id=ws.id,
        organization_id=ws.organization_id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        status=ws.status.value,
        created_at=ws.created_at,
        role=role.value if role else None,
    )
    return {"data": res}


@router.patch("/workspaces/{workspace_id}", dependencies=[Depends(require_csrf)])
def update_workspace(
    workspace_id: str,
    payload: UpdateWorkspaceRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.UPDATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, role = context
    try:
        updated = workspace_service.update_workspace(
            db=db,
            workspace_id=ws.id,
            actor_id=current_user.id,
            name=payload.name,
            description=payload.description,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    res = WorkspaceResponse(
        id=updated.id,
        organization_id=updated.organization_id,
        name=updated.name,
        slug=updated.slug,
        description=updated.description,
        status=updated.status.value,
        created_at=updated.created_at,
        role=role.value if role else None,
    )
    return {"data": res}


@router.post("/workspaces/{workspace_id}/archive", dependencies=[Depends(require_csrf)])
def archive_workspace(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.ARCHIVE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        workspace_service.archive_workspace(db, ws.id, current_user.id)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"message": f"Workspace '{ws.name}' has been archived."}}


@router.get("/workspaces/{workspace_id}/members")
def list_workspace_members(
    workspace_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MEMBERS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    members = workspace_service.list_workspace_members(db, ws.id)
    results = [
        WorkspaceMemberResponse(
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


@router.post("/workspaces/{workspace_id}/members", dependencies=[Depends(require_csrf)])
def add_workspace_member(
    workspace_id: str,
    payload: AddWorkspaceMemberRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MEMBERS_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        membership = workspace_service.add_workspace_member(
            db=db,
            workspace_id=ws.id,
            user_id=payload.user_id,
            role=payload.role,
            actor_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "data": {
            "workspace_id": membership.workspace_id,
            "user_id": membership.user_id,
            "role": membership.role.value,
        }
    }


@router.patch("/workspaces/{workspace_id}/members/{user_id}", dependencies=[Depends(require_csrf)])
def update_workspace_member_role(
    workspace_id: str,
    user_id: str,
    payload: UpdateWorkspaceMemberRoleRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MEMBERS_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        updated = workspace_service.update_workspace_member_role(
            db=db,
            workspace_id=ws.id,
            target_user_id=user_id,
            new_role=payload.role,
            actor_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"user_id": updated.user_id, "role": updated.role.value}}


@router.delete("/workspaces/{workspace_id}/members/{user_id}", dependencies=[Depends(require_csrf)])
def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.MEMBERS_MANAGE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        workspace_service.remove_workspace_member(
            db=db,
            workspace_id=ws.id,
            target_user_id=user_id,
            actor_id=current_user.id,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"data": {"message": "Member removed from workspace."}}
