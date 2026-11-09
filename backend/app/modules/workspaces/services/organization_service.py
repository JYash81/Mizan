"""Organization management service."""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.identity import AccountStatus, User
from app.models.organization import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    Workspace,
    WorkspaceMembership,
)
from app.modules.audit.services.audit_service import record_audit_event

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(slug: str) -> str:
    cleaned = slug.strip().lower()
    if not cleaned or len(cleaned) < 2 or len(cleaned) > 100:
        raise ValueError("Slug must be between 2 and 100 characters.")
    if not SLUG_PATTERN.match(cleaned):
        raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens.")
    return cleaned


def create_organization(
    db: Session,
    creator_id: str,
    name: str,
    slug: str,
    description: str | None = None,
) -> tuple[Organization, OrganizationMembership]:
    """Create a new organization and assign the creator as the initial OWNER."""
    creator = db.get(User, creator_id)
    if creator is None or creator.status != AccountStatus.ACTIVE:
        raise ValueError("Active creator user is required to create an organization.")

    valid_slug = validate_slug(slug)
    existing = db.scalar(select(Organization).where(Organization.slug == valid_slug))
    if existing is not None:
        raise ValueError(f"Organization slug '{valid_slug}' is already taken.")

    org = Organization(
        name=name.strip(),
        slug=valid_slug,
        description=description.strip() if description else None,
        created_by=creator.id,
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=creator.id,
        role=OrganizationRole.OWNER,
        membership_status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="ORGANIZATION_CREATED",
        resource_type="organization",
        resource_id=org.id,
        actor_user_id=creator.id,
        safe_metadata={"name": org.name, "slug": org.slug},
    )

    return org, membership


def get_organization(db: Session, organization_id: str) -> Organization | None:
    return db.get(Organization, organization_id)


def get_organization_by_slug(db: Session, slug: str) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.slug == slug.strip().lower()))


def list_user_organizations(
    db: Session, user_id: str
) -> list[tuple[Organization, OrganizationMembership]]:
    stmt = (
        select(Organization, OrganizationMembership)
        .join(
            OrganizationMembership,
            Organization.id == OrganizationMembership.organization_id,
        )
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.membership_status == MembershipStatus.ACTIVE,
            Organization.status != OrganizationStatus.ARCHIVED,
        )
        .order_by(Organization.name.asc())
    )
    return list(db.execute(stmt).all())


def update_organization(
    db: Session,
    organization_id: str,
    actor_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found.")

    if name is not None:
        org.name = name.strip()
    if description is not None:
        org.description = description.strip()

    db.flush()
    record_audit_event(
        db=db,
        event_type="ORGANIZATION_UPDATED",
        resource_type="organization",
        resource_id=org.id,
        actor_user_id=actor_id,
        safe_metadata={"name": org.name},
    )
    return org


def archive_organization(db: Session, organization_id: str, actor_id: str) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found.")

    org.status = OrganizationStatus.ARCHIVED
    db.flush()
    record_audit_event(
        db=db,
        event_type="ORGANIZATION_ARCHIVED",
        resource_type="organization",
        resource_id=org.id,
        actor_user_id=actor_id,
    )
    return org


def get_organization_member(
    db: Session, organization_id: str, user_id: str
) -> OrganizationMembership | None:
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user_id,
    )
    return db.scalar(stmt)


def list_organization_members(
    db: Session, organization_id: str
) -> list[tuple[OrganizationMembership, User]]:
    stmt = (
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.membership_status == MembershipStatus.ACTIVE,
        )
        .order_by(OrganizationMembership.role.asc(), User.full_name.asc())
    )
    return list(db.execute(stmt).all())


def add_organization_member(
    db: Session,
    organization_id: str,
    user_id: str,
    role: OrganizationRole,
    invited_by: str | None = None,
) -> OrganizationMembership:
    org = db.get(Organization, organization_id)
    if org is None or org.status != OrganizationStatus.ACTIVE:
        raise ValueError("Active organization not found.")

    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found.")

    existing = get_organization_member(db, organization_id, user_id)
    if existing is not None:
        raise ValueError("User is already a member of this organization.")

    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        membership_status=MembershipStatus.ACTIVE,
        invited_by=invited_by,
    )
    db.add(membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="ORGANIZATION_MEMBER_ADDED",
        resource_type="organization_membership",
        resource_id=membership.id,
        actor_user_id=invited_by,
        safe_metadata={"organization_id": org.id, "user_id": user.id, "role": role.value},
    )
    return membership


def update_organization_member_role(
    db: Session,
    organization_id: str,
    target_user_id: str,
    new_role: OrganizationRole,
    actor_id: str,
) -> OrganizationMembership:
    membership = get_organization_member(db, organization_id, target_user_id)
    if membership is None:
        raise ValueError("Membership not found.")

    # Guard: Cannot demote the last owner
    if membership.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
        owner_count = db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == OrganizationRole.OWNER,
                OrganizationMembership.membership_status == MembershipStatus.ACTIVE,
            )
        )
        if owner_count <= 1:
            raise ValueError("Cannot demote the sole active owner of the organization.")

    old_role = membership.role
    membership.role = new_role
    db.flush()

    record_audit_event(
        db=db,
        event_type="ORGANIZATION_MEMBER_ROLE_UPDATED",
        resource_type="organization_membership",
        resource_id=membership.id,
        actor_user_id=actor_id,
        safe_metadata={
            "target_user_id": target_user_id,
            "old_role": old_role.value,
            "new_role": new_role.value,
        },
    )
    return membership


def remove_organization_member(
    db: Session, organization_id: str, target_user_id: str, actor_id: str
) -> bool:
    membership = get_organization_member(db, organization_id, target_user_id)
    if membership is None:
        raise ValueError("Membership not found.")

    if membership.role == OrganizationRole.OWNER:
        owner_count = db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == OrganizationRole.OWNER,
                OrganizationMembership.membership_status == MembershipStatus.ACTIVE,
            )
        )
        if owner_count <= 1:
            raise ValueError("Cannot remove the sole active owner of the organization.")

    # Remove user from all workspaces in this organization
    org_workspaces = select(Workspace.id).where(Workspace.organization_id == organization_id)
    stmt = WorkspaceMembership.__table__.delete().where(
        WorkspaceMembership.user_id == target_user_id,
        WorkspaceMembership.workspace_id.in_(org_workspaces),
    )
    db.execute(stmt)

    db.delete(membership)
    db.flush()

    record_audit_event(
        db=db,
        event_type="ORGANIZATION_MEMBER_REMOVED",
        resource_type="organization_membership",
        resource_id=membership.id,
        actor_user_id=actor_id,
        safe_metadata={"organization_id": organization_id, "target_user_id": target_user_id},
    )
    return True


def transfer_organization_ownership(
    db: Session,
    organization_id: str,
    current_owner_id: str,
    new_owner_id: str,
) -> tuple[OrganizationMembership, OrganizationMembership]:
    current_owner_membership = get_organization_member(db, organization_id, current_owner_id)
    if current_owner_membership is None or current_owner_membership.role != OrganizationRole.OWNER:
        raise ValueError("Only an active owner can transfer organization ownership.")

    new_owner_membership = get_organization_member(db, organization_id, new_owner_id)
    if (
        new_owner_membership is None
        or new_owner_membership.membership_status != MembershipStatus.ACTIVE
    ):
        raise ValueError("New owner must be an active member of the organization.")

    current_owner_membership.role = OrganizationRole.ADMIN
    new_owner_membership.role = OrganizationRole.OWNER
    db.flush()

    record_audit_event(
        db=db,
        event_type="ORGANIZATION_OWNER_TRANSFERRED",
        resource_type="organization",
        resource_id=organization_id,
        actor_user_id=current_owner_id,
        safe_metadata={"previous_owner": current_owner_id, "new_owner": new_owner_id},
    )
    return current_owner_membership, new_owner_membership
