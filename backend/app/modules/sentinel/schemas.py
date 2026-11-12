"""Pydantic schemas for Sentinel v2 & Security Governance APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.sentinel import (
    ContainmentAction,
    ContainmentTargetType,
    OrderExecutionStatus,
    SealedEvidenceStatus,
    SupportAccessScope,
    SupportAccessStatus,
)

# =========================================================================
# 1. Sentinel Containment Order Schemas
# =========================================================================


class ContainmentOrderCreate(BaseModel):
    """Payload to request or issue a signed containment order."""

    workspace_id: str
    target_type: ContainmentTargetType
    target_id: str
    action: ContainmentAction
    reason: str
    duration_minutes: int = Field(default=15, ge=1, le=1440)
    is_cross_tenant: bool = False
    approver_1_id: str | None = None
    approver_2_id: str | None = None
    dual_approval_token: str | None = None


class ContainmentOrderRead(BaseModel):
    """Public details of a signed containment order."""

    id: str
    order_id: str
    workspace_id: str
    target_type: ContainmentTargetType
    target_id: str
    action: ContainmentAction
    reason: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    is_cross_tenant: bool
    dual_approved: bool
    approver_1_id: str | None
    approver_2_id: str | None
    signature: str
    canonical_payload: str = ""
    signature_purpose: str
    signer_key_id: str
    execution_status: OrderExecutionStatus
    executed_at: datetime | None
    executed_by_enforcer: str | None
    execution_details: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderExecutionRequest(BaseModel):
    """Payload sent by local runtime enforcer to execute an order."""

    order: ContainmentOrderRead
    enforcer_id: str
    local_workspace_id: str


class OrderExecutionResult(BaseModel):
    """Result of order execution by local enforcer."""

    order_id: str
    success: bool
    status: OrderExecutionStatus
    executed_at: datetime
    action_taken: str
    message: str


# =========================================================================
# 2. Support Access Broker Schemas
# =========================================================================


class SupportAccessCreateRequest(BaseModel):
    """Support staff request for just-in-time access."""

    ticket_id: str = Field(..., min_length=3, max_length=64)
    reason: str = Field(..., min_length=10)
    requested_scope: SupportAccessScope
    duration_minutes: int = Field(default=30, ge=5, le=480)
    is_break_glass: bool = False
    break_glass_reason: str | None = None


class SupportAccessApproveRequest(BaseModel):
    """Customer admin decision on a support access request."""

    second_approver_id: str | None = None


class SupportSessionLogRead(BaseModel):
    """Audit entry of staff action during JIT access."""

    id: str
    access_request_id: str
    workspace_id: str
    staff_user_id: str
    action: str
    resource: str
    request_method: str
    path: str
    status_code: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportAccessRead(BaseModel):
    """Customer-auditable support access request record."""

    id: str
    workspace_id: str
    ticket_id: str
    reason: str
    requested_by_staff_id: str
    requested_scope: SupportAccessScope
    duration_minutes: int
    status: SupportAccessStatus
    approved_by_customer_id: str | None
    approved_at: datetime | None
    second_approver_id: str | None
    second_approved_at: datetime | None
    token_id: str | None
    expires_at: datetime | None
    is_break_glass: bool
    break_glass_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 3. Sealed Evidence Vault Schemas
# =========================================================================


class SealedEvidenceCreateRequest(BaseModel):
    """Payload to seal raw prohibited content in forensic escrow."""

    incident_id: str
    raw_payload: str
    content_type: str = "text/plain"
    retention_days: int = Field(default=7, ge=1, le=90)


class SealedEvidenceUnsealRequest(BaseModel):
    """Dual-authorized request to inspect sealed evidence."""

    approver_1_id: str
    approver_2_id: str
    reason: str = Field(..., min_length=10)


class SealedEvidenceRead(BaseModel):
    """Metadata-first record of sealed forensic evidence."""

    id: str
    incident_id: str
    workspace_id: str
    content_digest: str
    content_type: str
    encryption_key_id: str
    status: SealedEvidenceStatus
    release_approver_1_id: str | None
    release_approver_2_id: str | None
    released_at: datetime | None
    purged_at: datetime | None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnsealedEvidenceResponse(BaseModel):
    """Unsealed plaintext evidence payload with audit metadata."""

    evidence_id: str
    incident_id: str
    content_type: str
    content_digest: str
    payload: str
    unsealed_at: datetime
    authorized_by: list[str]


# =========================================================================
# 4. Anti-Rollback Signed Version Floor Schemas
# =========================================================================


class SignedVersionFloorCreateRequest(BaseModel):
    """Payload to publish a new signed minimum-version floor."""

    minimum_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    workspace_id: str | None = None


class SignedVersionFloorRead(BaseModel):
    """Signed minimum-version floor details."""

    id: str
    workspace_id: str | None
    minimum_version: str
    effective_at: datetime
    nonce: str
    signature: str
    canonical_payload: str = ""
    signer_public_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 5. Regulatory Incident Clocks Schemas
# =========================================================================


class IncidentRegulatoryClockRead(BaseModel):
    """Regulatory and contractual clock tracking for an incident."""

    id: str
    incident_id: str
    workspace_id: str
    awareness_at: datetime
    gdpr_deadline: datetime
    customer_contract_deadline: datetime
    gdpr_notified_at: datetime | None
    customer_notified_at: datetime | None
    escalation_level: int
    last_escalated_at: datetime | None
    gdpr_hours_remaining: float
    contract_hours_remaining: float
    is_gdpr_breached: bool
    is_contract_breached: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 6. Sev1 Two-Person Recovery Schemas
# =========================================================================


class Sev1RecoveryInitiateRequest(BaseModel):
    """Initiates two-person recovery workflow for Sev1 containment."""

    incident_id: str | None = None
    target_type: str
    target_id: str
    triggering_actor_id: str
    reason: str = Field(..., min_length=10)


class Sev1RecoveryApproveRequest(BaseModel):
    """Approves and executes Sev1 recovery with dual authorization."""

    approver_1_id: str
    approver_2_id: str
    recovery_notes: str = Field(..., min_length=10)


class Sev1RecoveryRead(BaseModel):
    """Sev1 recovery workflow record."""

    id: str
    workspace_id: str
    incident_id: str | None
    target_type: str
    target_id: str
    triggering_actor_id: str
    reason: str
    approver_1_id: str | None
    approver_1_at: datetime | None
    approver_2_id: str | None
    approver_2_at: datetime | None
    integrity_check_passed: bool
    integrity_details: str | None
    status: str
    restored_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# 7. Fail-Behaviour Matrix Schemas
# =========================================================================


class DependencyStatusInput(BaseModel):
    """Status of system dependencies."""

    policy_engine_down: bool = False
    classifier_down: bool = False
    sentinel_unreachable: bool = False
    key_service_down: bool = False
    network_cut: bool = False


class FailBehaviourEvaluateRequest(BaseModel):
    """Evaluate permission and fail-behaviour for a protected operation."""

    operation: str
    dependencies: DependencyStatusInput
    is_data_classified_public: bool = False
    is_cached_policy_valid: bool = True
    policy_age_hours: float = 1.0
    max_policy_age_hours: float = 24.0
    is_cached_key_valid: bool = True
    is_tool_allowlisted: bool = True
    is_within_budget: bool = True


class FailBehaviourEvaluateResponse(BaseModel):
    """Evaluation result with deterministic fail-behaviour decision."""

    operation: str
    allowed: bool
    action: str
    quarantined: bool
    queued_telemetry: bool
    degraded_read_only: bool
    reason: str
