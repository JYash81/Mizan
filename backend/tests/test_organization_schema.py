import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
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
    WorkspaceStatus,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_organization_and_workspace_schema(db: Session):
    user = User(
        full_name="Founder Frank",
        email="frank@org.com",
        normalized_email="frank@org.com",
        password_hash="argon2id$mocked",
        status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.commit()

    # Create Organization
    org = Organization(
        name="Acme Corp",
        slug="acme-corp",
        description="The Acme Enterprise",
        created_by=user.id,
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.commit()

    # Add Owner Membership
    org_member = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
        membership_status=MembershipStatus.ACTIVE,
    )
    db.add(org_member)
    db.commit()

    # Duplicate membership for same org and user must violate unique constraint
    db.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=OrganizationRole.MEMBER,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Create Workspace
    ws = Workspace(
        organization_id=org.id,
        name="Default Workspace",
        slug="default",
        description="Main workspace",
        created_by=user.id,
        status=WorkspaceStatus.ACTIVE,
    )
    db.add(ws)
    db.commit()

    # Add Workspace Membership
    ws_member = WorkspaceMembership(
        workspace_id=ws.id,
        user_id=user.id,
        role=WorkspaceRole.WORKSPACE_OWNER,
        membership_status=MembershipStatus.ACTIVE,
    )
    db.add(ws_member)
    db.commit()

    # Duplicate workspace slug within the same org must fail
    db.add(
        Workspace(
            organization_id=org.id,
            name="Another Default",
            slug="default",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Duplicate org slug must fail
    db.add(
        Organization(
            name="Acme Duplicate",
            slug="acme-corp",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Create Invitation
    invitation = Invitation(
        organization_id=org.id,
        workspace_id=ws.id,
        invited_email="colleague@org.com",
        normalized_email="colleague@org.com",
        token_hash="hash1234567890",
        organization_role=OrganizationRole.MEMBER,
        workspace_role=WorkspaceRole.WORKSPACE_MEMBER,
        invited_by=user.id,
        status=InvitationStatus.PENDING,
        expires_at=user.created_at,
    )
    db.add(invitation)
    db.commit()

    stored_inv = db.get(Invitation, invitation.id)
    assert stored_inv is not None
    assert stored_inv.invited_email == "colleague@org.com"
