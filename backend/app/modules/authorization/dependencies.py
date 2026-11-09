"""Tenant-aware authorization and permission enforcement dependencies."""

from collections.abc import Callable

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    Workspace,
    WorkspaceRole,
    WorkspaceStatus,
)
from app.modules.auth.dependencies import get_current_active_user
from app.modules.authorization.permissions import OrganizationPermission, WorkspacePermission
from app.modules.authorization.rbac import (
    has_organization_permission,
    has_workspace_permission,
)
from app.modules.workspaces.services.organization_service import (
    get_organization,
    get_organization_member,
)
from app.modules.workspaces.services.workspace_service import (
    get_workspace,
    get_workspace_member,
)


def get_current_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> tuple[Organization, OrganizationMembership]:
    """Resolve and validate the active organization and user's membership.

    Returns a 404 rather than 403 if the organization does not exist or the user
    is not an active member, preventing unauthorized tenant-existence probing.
    """
    org = get_organization(db, organization_id)
    if org is None or org.status == OrganizationStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if org.status == OrganizationStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Organization is suspended. Contact support.")

    membership = get_organization_member(db, org.id, current_user.id)
    if membership is None or membership.membership_status != MembershipStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Organization not found.")

    return org, membership


def get_current_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> tuple[Workspace, OrganizationMembership, WorkspaceRole | None]:
    """Resolve and validate active workspace access with organization boundary enforcement."""
    ws = get_workspace(db, workspace_id)
    if ws is None or ws.status == WorkspaceStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    # Validate parent organization membership
    org = get_organization(db, ws.organization_id)
    if org is None or org.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    org_membership = get_organization_member(db, org.id, current_user.id)
    if org_membership is None or org_membership.membership_status != MembershipStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    # Org Owner automatically has full Workspace Owner rights
    if org_membership.role == OrganizationRole.OWNER:
        return ws, org_membership, WorkspaceRole.WORKSPACE_OWNER

    # Check explicit workspace membership
    ws_membership = get_workspace_member(db, ws.id, current_user.id)
    if ws_membership is None or ws_membership.membership_status != MembershipStatus.ACTIVE:
        # Org Admins have admin visibility if no specific membership exists
        if org_membership.role == OrganizationRole.ADMIN:
            return ws, org_membership, WorkspaceRole.WORKSPACE_ADMIN
        raise HTTPException(status_code=404, detail="Workspace not found.")

    return ws, org_membership, ws_membership.role


def require_org_permission(
    permission: OrganizationPermission,
) -> Callable[..., tuple[Organization, OrganizationMembership]]:
    """Factory dependency checking organization-level permissions."""

    def _dependency(
        context: tuple[Organization, OrganizationMembership] = Depends(get_current_organization),
    ) -> tuple[Organization, OrganizationMembership]:
        org, membership = context
        if not has_organization_permission(membership.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value} required.",
            )
        return org, membership

    return _dependency


def require_ws_permission(
    permission: WorkspacePermission,
) -> Callable[..., tuple[Workspace, OrganizationMembership, WorkspaceRole | None]]:
    """Factory dependency checking workspace-level permissions."""

    def _dependency(
        context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
            get_current_workspace
        ),
    ) -> tuple[Workspace, OrganizationMembership, WorkspaceRole | None]:
        ws, org_membership, ws_role = context
        if not has_workspace_permission(org_membership.role, ws_role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value} required.",
            )
        return ws, org_membership, ws_role

    return _dependency
