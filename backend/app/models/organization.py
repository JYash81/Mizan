import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class OrganizationRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class WorkspaceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class WorkspaceRole(str, enum.Enum):
    WORKSPACE_OWNER = "WORKSPACE_OWNER"
    WORKSPACE_ADMIN = "WORKSPACE_ADMIN"
    WORKSPACE_MEMBER = "WORKSPACE_MEMBER"
    WORKSPACE_VIEWER = "WORKSPACE_VIEWER"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


ORGANIZATION_STATUS = Enum(
    OrganizationStatus,
    native_enum=False,
    create_constraint=True,
    name="organization_status",
)
ORGANIZATION_ROLE = Enum(
    OrganizationRole,
    native_enum=False,
    create_constraint=True,
    name="organization_role",
)
WORKSPACE_STATUS = Enum(
    WorkspaceStatus,
    native_enum=False,
    create_constraint=True,
    name="workspace_status",
)
WORKSPACE_ROLE = Enum(
    WorkspaceRole,
    native_enum=False,
    create_constraint=True,
    name="workspace_role",
)
MEMBERSHIP_STATUS = Enum(
    MembershipStatus,
    native_enum=False,
    create_constraint=True,
    name="membership_status",
)
INVITATION_STATUS = Enum(
    InvitationStatus,
    native_enum=False,
    create_constraint=True,
    name="invitation_status",
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        ORGANIZATION_STATUS, default=OrganizationStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[OrganizationRole] = mapped_column(
        ORGANIZATION_ROLE, default=OrganizationRole.MEMBER
    )
    membership_status: Mapped[MembershipStatus] = mapped_column(
        MEMBERSHIP_STATUS, default=MembershipStatus.ACTIVE
    )
    invited_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[WorkspaceStatus] = mapped_column(
        WORKSPACE_STATUS, default=WorkspaceStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[WorkspaceRole] = mapped_column(
        WORKSPACE_ROLE, default=WorkspaceRole.WORKSPACE_MEMBER
    )
    membership_status: Mapped[MembershipStatus] = mapped_column(
        MEMBERSHIP_STATUS, default=MembershipStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), index=True)
    invited_email: Mapped[str] = mapped_column(String(320))
    normalized_email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    organization_role: Mapped[OrganizationRole] = mapped_column(
        ORGANIZATION_ROLE, default=OrganizationRole.MEMBER
    )
    workspace_role: Mapped[WorkspaceRole | None] = mapped_column(WORKSPACE_ROLE)
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        INVITATION_STATUS, default=InvitationStatus.PENDING
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
