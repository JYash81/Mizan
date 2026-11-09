"""Pydantic schemas for organizations, workspaces, memberships, and invitations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization import OrganizationRole, WorkspaceRole


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    status: str
    created_at: datetime
    role: str


class OrganizationMemberResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    membership_status: str
    created_at: datetime


class UpdateMemberRoleRequest(BaseModel):
    role: OrganizationRole


class TransferOwnershipRequest(BaseModel):
    new_owner_id: str


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    slug: str
    description: str | None
    status: str
    created_at: datetime
    role: str | None = None


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    membership_status: str
    created_at: datetime


class AddWorkspaceMemberRequest(BaseModel):
    user_id: str
    role: WorkspaceRole = WorkspaceRole.WORKSPACE_MEMBER


class UpdateWorkspaceMemberRoleRequest(BaseModel):
    role: WorkspaceRole


class CreateInvitationRequest(BaseModel):
    email: EmailStr
    organization_role: OrganizationRole = OrganizationRole.MEMBER
    workspace_id: str | None = None
    workspace_role: WorkspaceRole | None = None


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    workspace_id: str | None
    invited_email: str
    organization_role: str
    workspace_role: str | None
    status: str
    expires_at: datetime
    created_at: datetime


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=128)
