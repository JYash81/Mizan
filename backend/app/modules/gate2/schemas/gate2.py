"""Pydantic schemas for Gate 2 Financial Approval & Governance."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.gate2 import Gate2ApprovalStatus


class Gate2ApprovalEventResponse(BaseModel):
    """Event log audit record response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    approval_request_id: str
    actor_id: str
    event_type: str
    previous_status: str | None = None
    new_status: str
    message: str | None = None
    metadata_json: str | None = None
    created_at: datetime


class Gate2ApprovalRequestCreate(BaseModel):
    """Input payload to create a new Gate 2 financial approval request."""

    title: str = Field(..., min_length=3, max_length=255)
    purpose: str = Field(..., min_length=5)
    workload_type: str = Field(default="EXPERIMENT_EVALUATION", max_length=64)

    hardware_profile_key: str = Field(..., max_length=64)
    provider_name: str = Field(default="local", max_length=64)
    instance_type: str = Field(default="local-i5", max_length=64)
    region: str = Field(default="local", max_length=64)

    estimated_duration_hours: float = Field(..., gt=0.0)
    max_duration_hours: float = Field(..., gt=0.0)
    max_authorized_budget: Decimal = Field(..., ge=0.0)
    currency: str = Field(default="USD", max_length=8)

    dataset_id: str | None = None
    dataset_version_id: str | None = None
    gate1_approval_id: str | None = None
    experiment_id: str | None = None


class Gate2ApprovalRequestResponse(BaseModel):
    """Complete response model for a Gate 2 approval request."""

    id: str
    organization_id: str
    workspace_id: str
    requester_id: str

    title: str
    purpose: str
    workload_type: str

    dataset_id: str | None = None
    dataset_version_id: str | None = None
    gate1_approval_id: str | None = None
    experiment_id: str | None = None

    hardware_profile_key: str
    provider_name: str
    instance_type: str
    region: str
    estimated_duration_hours: float
    max_duration_hours: float

    estimated_compute_cost: str
    estimated_storage_cost: str
    estimated_total_cost: str
    max_authorized_budget: str
    currency: str

    proposal_digest: str
    proposal_payload_json: str
    pricing_snapshot_json: str
    pricing_catalog_version: str

    status: Gate2ApprovalStatus
    approver_id: str | None = None
    approver_role_snapshot: str | None = None
    approval_signature: str | None = None
    signing_key_id: str | None = None
    signed_payload: str | None = None
    signed_at: datetime | None = None

    decision_reason: str | None = None
    rejection_reason: str | None = None
    revocation_reason: str | None = None
    revoked_by_id: str | None = None
    revoked_at: datetime | None = None

    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    events: list[Gate2ApprovalEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class Gate2DecisionRequest(BaseModel):
    """Request payload to approve or reject a Gate 2 approval request."""

    decision: str = Field(..., pattern="^(APPROVE|REJECT)$")
    decision_reason: str = Field(..., min_length=3)
    signing_key_id: str | None = None


class Gate2RevokeRequest(BaseModel):
    """Request payload to revoke a previously approved Gate 2 request."""

    revocation_reason: str = Field(..., min_length=3)


class FinancialAuthorizationRequest(BaseModel):
    """Query payload to test whether a workload is authorized to execute."""

    approval_request_id: str
    proposed_cost: Decimal | None = None


class FinancialAuthorizationResponse(BaseModel):
    """Result of policy and cryptographic check for execution readiness."""

    authorized: bool
    status: Gate2ApprovalStatus
    reason: str
    proposal_digest_match: bool
    signature_valid: bool
    policy_allowed: bool
    max_authorized_budget: str | None = None
    estimated_total_cost: str | None = None
    expires_at: datetime | None = None
    details: dict[str, Any] = {}
