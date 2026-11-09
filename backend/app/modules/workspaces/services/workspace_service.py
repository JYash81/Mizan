"""Workspace management service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User
from app.models.organization import (
    MembershipStatus,
    Organization,
    OrganizationRole,
    OrganizationStatus,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    WorkspaceStatus,
)
from app.modules.audit.services.audit_service import record_audit_event
from app.modules.workspaces.services.organization_service import (
    get_organization_member,
    validate_slug,
)


def create_workspace(
    db: Session,
    organization_id: str,
    creator_id: str,
    name: str,
    slug: str,
    description: str | None = None,
) -> tuple[Workspace, WorkspaceMembership]:
    """Create a new workspace within an organization and assign creator as WORKSPACE_OWNER."""
    org = db.get(Organization, organization_id)
    if org is None or org.status != OrganizationStatus.ACTIVE:
        raise ValueError("Active organization required to create workspace.")

    org_member = get_organization_member(db, organization_id, creator_id)
    if org_member is None or org_member.membership_status != MembershipStatus.ACTIVE:
        raise ValueError("Creator must be an active member of the organization.")

    valid_slug = validate_slug(slug)
    existing = db.scalar(
        select(Workspace).where(
            Workspace.organization_id == organization_id,
            Workspace.slug == valid_slug,
        )
    )
    if existing is not None:
        raise ValueError(f"Workspace slug '{valid_slug}' already exists in this organization.")

    ws = Workspace(
        organization_id=org.id,
        name=name.strip(),
        slug=valid_slug,
        description=description.strip() if description else None,
        created_by=creator_id,
        status=WorkspaceStatus.ACTIVE,
    )
    db.add(ws)
    db.flush()

    ws_membership = WorkspaceMembership(
        workspace_id=ws.id,
        user_id=creator_id,
        role=WorkspaceRole.WORKSPACE_OWNER,
        membership_status=MembershipStatus.ACTIVE,
    )
    db.add(ws_membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="WORKSPACE_CREATED",
        resource_type="workspace",
        resource_id=ws.id,
        actor_user_id=creator_id,
        safe_metadata={"organization_id": org.id, "name": ws.name, "slug": ws.slug},
    )

    return ws, ws_membership


def get_workspace(db: Session, workspace_id: str) -> Workspace | None:
    return db.get(Workspace, workspace_id)


def get_workspace_by_slug(db: Session, organization_id: str, slug: str) -> Workspace | None:
    return db.scalar(
        select(Workspace).where(
            Workspace.organization_id == organization_id,
            Workspace.slug == slug.strip().lower(),
        )
    )


def list_organization_workspaces(
    db: Session,
    organization_id: str,
    user_id: str,
) -> list[tuple[Workspace, WorkspaceRole | None]]:
    """List workspaces in an organization accessible to the user.

    Org Owners and Admins have visibility into all active workspaces.
    Standard members see only workspaces where they hold active membership.
    """
    org_member = get_organization_member(db, organization_id, user_id)
    if org_member is None or org_member.membership_status != MembershipStatus.ACTIVE:
        return []

    is_privileged = org_member.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)

    if is_privileged:
        # Org Owner/Admin sees all active workspaces
        workspaces = list(
            db.scalars(
                select(Workspace)
                .where(
                    Workspace.organization_id == organization_id,
                    Workspace.status != WorkspaceStatus.ARCHIVED,
                )
                .order_by(Workspace.name.asc())
            ).all()
        )
        results = []
        for ws in workspaces:
            member = get_workspace_member(db, ws.id, user_id)
            effective_role = (
                member.role
                if member
                else (
                    WorkspaceRole.WORKSPACE_OWNER
                    if org_member.role == OrganizationRole.OWNER
                    else WorkspaceRole.WORKSPACE_ADMIN
                )
            )
            results.append((ws, effective_role))
        return results

    # Regular members: joined query
    stmt = (
        select(Workspace, WorkspaceMembership.role)
        .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            Workspace.organization_id == organization_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.membership_status == MembershipStatus.ACTIVE,
            Workspace.status != WorkspaceStatus.ARCHIVED,
        )
        .order_by(Workspace.name.asc())
    )
    return list(db.execute(stmt).all())


def update_workspace(
    db: Session,
    workspace_id: str,
    actor_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise ValueError("Workspace not found.")

    if name is not None:
        ws.name = name.strip()
    if description is not None:
        ws.description = description.strip()

    db.flush()
    record_audit_event(
        db=db,
        event_type="WORKSPACE_UPDATED",
        resource_type="workspace",
        resource_id=ws.id,
        actor_user_id=actor_id,
        safe_metadata={"name": ws.name},
    )
    return ws


def archive_workspace(db: Session, workspace_id: str, actor_id: str) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise ValueError("Workspace not found.")

    ws.status = WorkspaceStatus.ARCHIVED
    db.flush()
    record_audit_event(
        db=db,
        event_type="WORKSPACE_ARCHIVED",
        resource_type="workspace",
        resource_id=ws.id,
        actor_user_id=actor_id,
    )
    return ws


def get_workspace_member(
    db: Session, workspace_id: str, user_id: str
) -> WorkspaceMembership | None:
    stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user_id,
    )
    return db.scalar(stmt)


def list_workspace_members(
    db: Session, workspace_id: str
) -> list[tuple[WorkspaceMembership, User]]:
    stmt = (
        select(WorkspaceMembership, User)
        .join(User, WorkspaceMembership.user_id == User.id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.membership_status == MembershipStatus.ACTIVE,
        )
        .order_by(WorkspaceMembership.role.asc(), User.full_name.asc())
    )
    return list(db.execute(stmt).all())


def add_workspace_member(
    db: Session,
    workspace_id: str,
    user_id: str,
    role: WorkspaceRole,
    actor_id: str,
) -> WorkspaceMembership:
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.status != WorkspaceStatus.ACTIVE:
        raise ValueError("Active workspace not found.")

    # Cross-tenant guard: User must belong to the workspace's parent organization
    org_member = get_organization_member(db, ws.organization_id, user_id)
    if org_member is None or org_member.membership_status != MembershipStatus.ACTIVE:
        raise ValueError("User must be an active member of the parent organization.")

    existing = get_workspace_member(db, workspace_id, user_id)
    if existing is not None:
        raise ValueError("User is already a member of this workspace.")

    membership = WorkspaceMembership(
        workspace_id=ws.id,
        user_id=user_id,
        role=role,
        membership_status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="WORKSPACE_MEMBER_ADDED",
        resource_type="workspace_membership",
        resource_id=membership.id,
        actor_user_id=actor_id,
        safe_metadata={
            "workspace_id": ws.id,
            "user_id": user_id,
            "role": role.value,
        },
    )
    return membership


def update_workspace_member_role(
    db: Session,
    workspace_id: str,
    target_user_id: str,
    new_role: WorkspaceRole,
    actor_id: str,
) -> WorkspaceMembership:
    membership = get_workspace_member(db, workspace_id, target_user_id)
    if membership is None:
        raise ValueError("Workspace membership not found.")

    old_role = membership.role
    membership.role = new_role
    db.flush()

    record_audit_event(
        db=db,
        event_type="WORKSPACE_MEMBER_ROLE_UPDATED",
        resource_type="workspace_membership",
        resource_id=membership.id,
        actor_user_id=actor_id,
        safe_metadata={
            "target_user_id": target_user_id,
            "old_role": old_role.value,
            "new_role": new_role.value,
        },
    )
    return membership


def remove_workspace_member(
    db: Session, workspace_id: str, target_user_id: str, actor_id: str
) -> bool:
    membership = get_workspace_member(db, workspace_id, target_user_id)
    if membership is None:
        raise ValueError("Workspace membership not found.")

    db.delete(membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="WORKSPACE_MEMBER_REMOVED",
        resource_type="workspace_membership",
        resource_id=membership.id,
        actor_user_id=actor_id,
        safe_metadata={"workspace_id": workspace_id, "target_user_id": target_user_id},
    )
    return True
