"""Organization and workspace invitation service."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.identity import AccountStatus, User
from app.models.organization import (
    Invitation,
    InvitationStatus,
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.modules.audit.services.audit_service import record_audit_event
from app.modules.email.provider import get_email_provider
from app.modules.workspaces.services.organization_service import get_organization_member


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def create_invitation(
    db: Session,
    organization_id: str,
    invited_by_id: str,
    email: str,
    org_role: OrganizationRole = OrganizationRole.MEMBER,
    workspace_id: str | None = None,
    ws_role: WorkspaceRole | None = None,
    expires_in_days: int = 7,
) -> tuple[Invitation, str]:
    org = db.get(Organization, organization_id)
    if org is None or org.status != OrganizationStatus.ACTIVE:
        raise ValueError("Active organization required to issue invitation.")

    inviter = db.get(User, invited_by_id)
    if inviter is None or inviter.status != AccountStatus.ACTIVE:
        raise ValueError("Active inviter user required.")

    # Validate workspace belongs to the organization if specified
    if workspace_id is not None:
        ws = db.get(Workspace, workspace_id)
        if ws is None or ws.organization_id != organization_id:
            raise ValueError("Workspace does not belong to the target organization.")
        if ws_role is None:
            ws_role = WorkspaceRole.WORKSPACE_MEMBER

    normalized_email = email.strip().lower()

    # Check if target email already has an active account with membership in this org
    existing_user = db.scalar(select(User).where(User.normalized_email == normalized_email))
    if existing_user is not None:
        existing_member = get_organization_member(db, organization_id, existing_user.id)
        if (
            existing_member is not None
            and existing_member.membership_status == MembershipStatus.ACTIVE
        ):
            raise ValueError("User is already an active member of this organization.")

    # Revoke any prior pending invitations for this email in this organization
    now = datetime.now(UTC)
    db.execute(
        update(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.normalized_email == normalized_email,
            Invitation.status == InvitationStatus.PENDING,
        )
        .values(status=InvitationStatus.REVOKED, revoked_at=now)
    )

    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=org.id,
        workspace_id=workspace_id,
        invited_email=email.strip(),
        normalized_email=normalized_email,
        token_hash=_digest(raw_token),
        organization_role=org_role,
        workspace_role=ws_role,
        invited_by=invited_by_id,
        status=InvitationStatus.PENDING,
        expires_at=now + timedelta(days=expires_in_days),
        created_at=now,
    )
    db.add(invitation)
    db.flush()

    # Dispatch email through EmailProvider
    email_provider = get_email_provider()
    email_provider.send_invitation_email(
        email=email.strip(),
        token=raw_token,
        organization_name=org.name,
        inviter_name=inviter.full_name,
        role=org_role.value,
    )

    record_audit_event(
        db=db,
        event_type="INVITATION_CREATED",
        resource_type="invitation",
        resource_id=invitation.id,
        actor_user_id=invited_by_id,
        safe_metadata={
            "organization_id": org.id,
            "workspace_id": workspace_id,
            "role": org_role.value,
        },
    )

    return invitation, raw_token


def get_invitation_by_token(db: Session, raw_token: str) -> Invitation | None:
    if not isinstance(raw_token, str) or not raw_token:
        return None

    digest = _digest(raw_token)
    invitation = db.scalar(
        select(Invitation).where(
            Invitation.token_hash == digest,
            Invitation.status == InvitationStatus.PENDING,
        )
    )
    if invitation is None:
        return None

    if _utc(invitation.expires_at) <= datetime.now(UTC):
        return None

    return invitation


def accept_invitation(
    db: Session,
    raw_token: str,
    accepting_user_id: str,
) -> tuple[OrganizationMembership, WorkspaceMembership | None]:
    """Atomically accept an invitation and grant organization and workspace memberships."""
    invitation = get_invitation_by_token(db, raw_token)
    if invitation is None:
        raise ValueError("Invalid or expired invitation token.")

    user = db.get(User, accepting_user_id)
    if user is None or user.status != AccountStatus.ACTIVE:
        raise ValueError("Active user required to accept an invitation.")

    # Strict email matching: user accepting MUST match invited email
    if user.normalized_email.lower() != invitation.normalized_email.lower():
        raise ValueError("The authenticated user email does not match the invitation email.")

    now = datetime.now(UTC)

    # Atomic conditional update prevents concurrent double-acceptance
    stmt = (
        update(Invitation)
        .where(
            Invitation.id == invitation.id,
            Invitation.status == InvitationStatus.PENDING,
        )
        .values(status=InvitationStatus.ACCEPTED, accepted_at=now)
        .execution_options(synchronize_session="fetch")
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        raise ValueError("Invitation is no longer available.")

    # 1. Organization Membership
    existing_org_member = get_organization_member(db, invitation.organization_id, user.id)
    if existing_org_member is not None:
        org_membership = existing_org_member
        org_membership.role = invitation.organization_role
        org_membership.membership_status = MembershipStatus.ACTIVE
    else:
        org_membership = OrganizationMembership(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.organization_role,
            membership_status=MembershipStatus.ACTIVE,
            invited_by=invitation.invited_by,
        )
        db.add(org_membership)
    db.flush()

    # 2. Workspace Membership (if applicable)
    ws_membership = None
    if invitation.workspace_id and invitation.workspace_role:
        existing_ws_member = db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        if existing_ws_member is not None:
            ws_membership = existing_ws_member
            ws_membership.role = invitation.workspace_role
            ws_membership.membership_status = MembershipStatus.ACTIVE
        else:
            ws_membership = WorkspaceMembership(
                workspace_id=invitation.workspace_id,
                user_id=user.id,
                role=invitation.workspace_role,
                membership_status=MembershipStatus.ACTIVE,
            )
            db.add(ws_membership)
        db.flush()

    record_audit_event(
        db=db,
        event_type="INVITATION_ACCEPTED",
        resource_type="invitation",
        resource_id=invitation.id,
        actor_user_id=user.id,
        safe_metadata={
            "organization_id": invitation.organization_id,
            "workspace_id": invitation.workspace_id,
        },
    )

    return org_membership, ws_membership


def reject_invitation(db: Session, raw_token: str, user_id: str) -> bool:
    invitation = get_invitation_by_token(db, raw_token)
    if invitation is None:
        return False

    now = datetime.now(UTC)
    result = db.execute(
        update(Invitation)
        .where(Invitation.id == invitation.id, Invitation.status == InvitationStatus.PENDING)
        .values(status=InvitationStatus.REJECTED, revoked_at=now)
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount == 1:
        record_audit_event(
            db=db,
            event_type="INVITATION_REJECTED",
            resource_type="invitation",
            resource_id=invitation.id,
            actor_user_id=user_id,
        )
        return True
    return False


def revoke_invitation(db: Session, invitation_id: str, actor_id: str) -> bool:
    now = datetime.now(UTC)
    result = db.execute(
        update(Invitation)
        .where(Invitation.id == invitation_id, Invitation.status == InvitationStatus.PENDING)
        .values(status=InvitationStatus.REVOKED, revoked_at=now)
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount == 1:
        record_audit_event(
            db=db,
            event_type="INVITATION_REVOKED",
            resource_type="invitation",
            resource_id=invitation_id,
            actor_user_id=actor_id,
        )
        return True
    return False


def list_organization_invitations(db: Session, organization_id: str) -> list[Invitation]:
    stmt = (
        select(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.status == InvitationStatus.PENDING,
            Invitation.expires_at > datetime.now(UTC),
        )
        .order_by(Invitation.created_at.desc())
    )
    return list(db.scalars(stmt).all())
