"""Sentinel v2 and Security Governance REST API Endpoints.

Implements the Mizan Security Strategy v2:
- Detect: Ingest, correlate, dedup, and AI summary of security events.
- Decide: Deterministic policy evaluation, blast-radius limits, and Ed25519 order signing.
- Act: Local runtime enforcer order execution with signature, tenant, and nonce replay verification.
- Support Access Broker: JIT credential requests, customer approvals, and real-time session logs.
- Sealed Evidence Vault: AES-GCM forensic escrow with dual authorization.
- Anti-Rollback: Signed minimum-version floor publication and retrieval.
- Regulatory Clocks: GDPR 72-hour and contractual deadline tracking.
- Recovery: Two-person Sev1 recovery workflow with separation of duties.
- Fail-Behaviour: Deterministic evaluation of protected operations during dependency failures.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.observability import IncidentSeverity
from app.models.organization import Workspace
from app.modules.auth.dependencies import get_current_active_user
from app.modules.authorization.dependencies import get_current_workspace
from app.modules.sentinel.act_enforcer import execute_containment_order
from app.modules.sentinel.anti_rollback_service import (
    get_active_version_floor,
    publish_minimum_version_floor,
)
from app.modules.sentinel.decide_service import (
    evaluate_and_issue_containment_order,
)
from app.modules.sentinel.detect_service import (
    ingest_security_event,
)
from app.modules.sentinel.exceptions import (
    BlastRadiusLimitExceededError,
    DualApprovalRequiredError,
    EvidenceQuorumRequiredError,
    EvidenceSealedError,
    OrderExpiredError,
    OrderSignatureVerificationError,
    RecoveryIntegrityCheckFailedError,
    RecoveryQuorumError,
    ReplayedNonceError,
    SupportAccessDeniedError,
    TenantScopeMismatchError,
)
from app.modules.sentinel.fail_behaviour_matrix import evaluate_fail_behaviour
from app.modules.sentinel.recovery_service import (
    approve_and_execute_sev1_recovery,
    initiate_sev1_recovery,
)
from app.modules.sentinel.regulatory_clocks import (
    check_and_escalate_unacknowledged_incidents,
    get_incident_regulatory_clock,
)
from app.modules.sentinel.schemas import (
    ContainmentOrderCreate,
    ContainmentOrderRead,
    FailBehaviourEvaluateRequest,
    FailBehaviourEvaluateResponse,
    IncidentRegulatoryClockRead,
    OrderExecutionRequest,
    OrderExecutionResult,
    SealedEvidenceCreateRequest,
    SealedEvidenceRead,
    SealedEvidenceUnsealRequest,
    Sev1RecoveryApproveRequest,
    Sev1RecoveryInitiateRequest,
    Sev1RecoveryRead,
    SignedVersionFloorCreateRequest,
    SignedVersionFloorRead,
    SupportAccessApproveRequest,
    SupportAccessCreateRequest,
    SupportAccessRead,
    SupportSessionLogRead,
    UnsealedEvidenceResponse,
)
from app.modules.sentinel.sealed_evidence_vault import (
    seal_evidence,
    unseal_evidence_dual_approval,
)
from app.modules.sentinel.support_access_broker import (
    approve_support_access,
    list_support_requests,
    list_support_session_logs,
    request_support_access,
    revoke_support_access,
)

router = APIRouter(prefix="/sentinel", tags=["sentinel"])


# =========================================================================
# 1. Sentinel Detect & Decide Endpoints
# =========================================================================


@router.post("/detect/events", response_model=dict[str, Any])
def submit_security_telemetry_event(
    event_type: str,
    source: str,
    details: dict[str, Any],
    severity: IncidentSeverity = IncidentSeverity.SEV2,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> dict[str, Any]:
    """Ingests, correlates, deduplicates, and drafts AI summaries for security events."""
    return ingest_security_event(
        db=db,
        workspace_id=workspace.id,
        source=source,
        event_type=event_type,
        details=details,
        severity=severity,
        actor_id=current_user.id,
    )


@router.post("/decide/containment-orders", response_model=ContainmentOrderRead)
def issue_containment_order(
    payload: ContainmentOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> ContainmentOrderRead:
    """Evaluates deterministic policy and issues a signed, scoped containment order."""
    if payload.workspace_id != workspace.id and not payload.is_cross_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot issue single-tenant containment order for an unrelated workspace.",
        )
    try:
        return evaluate_and_issue_containment_order(db=db, payload=payload)
    except DualApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BlastRadiusLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc


@router.post("/act/execute-order", response_model=OrderExecutionResult)
def execute_order_on_enforcer(
    payload: OrderExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderExecutionResult:
    """Local runtime enforcer executes a cryptographically signed containment order."""
    try:
        return execute_containment_order(
            db=db,
            order=payload.order,
            enforcer_id=payload.enforcer_id,
            local_workspace_id=payload.local_workspace_id,
        )
    except TenantScopeMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except OrderExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OrderSignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ReplayedNonceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


# =========================================================================
# 2. Support Access Broker Endpoints
# =========================================================================


@router.post("/support-access/request", response_model=SupportAccessRead)
def create_support_request(
    payload: SupportAccessCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> SupportAccessRead:
    """Mizan support staff requests just-in-time access to a customer workspace."""
    return request_support_access(
        db=db,
        workspace_id=workspace.id,
        staff_user_id=current_user.id,
        payload=payload,
    )


@router.get("/support-access", response_model=list[SupportAccessRead])
def get_support_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> list[SupportAccessRead]:
    """Lists support requests for customer inspection."""
    return list_support_requests(db=db, workspace_id=workspace.id)


@router.post("/support-access/{request_id}/approve", response_model=SupportAccessRead)
def approve_support_request_endpoint(
    request_id: str,
    payload: SupportAccessApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SupportAccessRead:
    """Customer administrator approves JIT support credentials."""
    try:
        return approve_support_access(
            db=db,
            request_id=request_id,
            customer_admin_id=current_user.id,
            second_mizan_approver_id=payload.second_approver_id,
        )
    except SupportAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DualApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/support-access/{request_id}/revoke", response_model=SupportAccessRead)
def revoke_support_request_endpoint(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SupportAccessRead:
    """Customer administrator immediately revokes support access."""
    return revoke_support_access(db=db, request_id=request_id, revoked_by_id=current_user.id)


@router.get("/support-access/{request_id}/logs", response_model=list[SupportSessionLogRead])
def get_session_logs_endpoint(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> list[SupportSessionLogRead]:
    """Retrieves customer-visible audit logs of support staff actions."""
    return list_support_session_logs(db=db, workspace_id=workspace.id, access_request_id=request_id)


# =========================================================================
# 3. Sealed Evidence Vault Endpoints
# =========================================================================


@router.post("/evidence/seal", response_model=SealedEvidenceRead)
def seal_evidence_endpoint(
    payload: SealedEvidenceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> SealedEvidenceRead:
    """Encrypts raw prohibited content in sealed forensic escrow."""
    return seal_evidence(db=db, workspace_id=workspace.id, payload=payload)


@router.post("/evidence/{evidence_id}/unseal", response_model=UnsealedEvidenceResponse)
def unseal_evidence_endpoint(
    evidence_id: str,
    payload: SealedEvidenceUnsealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UnsealedEvidenceResponse:
    """Dual-authorized release of sealed forensic evidence."""
    try:
        return unseal_evidence_dual_approval(
            db=db,
            evidence_id=evidence_id,
            approver_1_id=payload.approver_1_id,
            approver_2_id=payload.approver_2_id,
            reason=payload.reason,
        )
    except EvidenceQuorumRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EvidenceSealedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# =========================================================================
# 4. Anti-Rollback Signed Minimum-Version Floor
# =========================================================================


@router.get("/version-floor", response_model=SignedVersionFloorRead | None)
def get_version_floor_endpoint(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
) -> SignedVersionFloorRead | None:
    """Retrieves the latest signed minimum-version floor."""
    return get_active_version_floor(db=db, workspace_id=workspace.id)


@router.post("/version-floor", response_model=SignedVersionFloorRead)
def publish_version_floor_endpoint(
    payload: SignedVersionFloorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> SignedVersionFloorRead:
    """Publishes a new cryptographically signed minimum-version floor."""
    target_ws = payload.workspace_id or workspace.id
    return publish_minimum_version_floor(
        db=db, minimum_version=payload.minimum_version, workspace_id=target_ws
    )


# =========================================================================
# 5. Regulatory Clocks & Timed Escalation
# =========================================================================


@router.get("/regulatory-clocks/{incident_id}", response_model=IncidentRegulatoryClockRead | None)
def get_regulatory_clock_endpoint(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IncidentRegulatoryClockRead | None:
    """Retrieves GDPR and contractual clock tracking for an incident."""
    clock = get_incident_regulatory_clock(db=db, incident_id=incident_id)
    if not clock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Regulatory clock not found."
        )
    return clock


@router.post("/regulatory-clocks/escalate", response_model=list[dict[str, Any]])
def trigger_escalation_endpoint(
    timeout_minutes: int = Query(default=15, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> list[dict[str, Any]]:
    """Evaluates unacknowledged incidents and triggers scheduled escalation."""
    return check_and_escalate_unacknowledged_incidents(
        db=db, workspace_id=workspace.id, escalation_timeout_minutes=timeout_minutes
    )


# =========================================================================
# 6. Sev1 Two-Person Recovery
# =========================================================================


@router.post("/recovery/sev1/initiate", response_model=Sev1RecoveryRead)
def initiate_recovery_endpoint(
    payload: Sev1RecoveryInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Sev1RecoveryRead:
    """Initiates a two-person Sev1 recovery workflow."""
    return initiate_sev1_recovery(db=db, workspace_id=workspace.id, payload=payload)


@router.post("/recovery/sev1/{recovery_id}/approve", response_model=Sev1RecoveryRead)
def approve_recovery_endpoint(
    recovery_id: str,
    payload: Sev1RecoveryApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Sev1RecoveryRead:
    """Approves and restores Sev1 contained service under dual authorization."""
    try:
        return approve_and_execute_sev1_recovery(
            db=db,
            recovery_id=recovery_id,
            approver_1_id=payload.approver_1_id,
            approver_2_id=payload.approver_2_id,
        )
    except RecoveryQuorumError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecoveryIntegrityCheckFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)
        ) from exc


# =========================================================================
# 7. Fail-Behaviour Matrix Evaluation Endpoint
# =========================================================================


@router.post("/fail-matrix/evaluate", response_model=FailBehaviourEvaluateResponse)
def evaluate_fail_behaviour_endpoint(
    payload: FailBehaviourEvaluateRequest,
) -> FailBehaviourEvaluateResponse:
    """Evaluates deterministic fail-behaviour policy for protected operations."""
    return evaluate_fail_behaviour(
        operation=payload.operation,
        dependencies=payload.dependencies,
        is_data_classified_public=payload.is_data_classified_public,
        is_cached_policy_valid=payload.is_cached_policy_valid,
        policy_age_hours=payload.policy_age_hours,
        max_policy_age_hours=payload.max_policy_age_hours,
        is_cached_key_valid=payload.is_cached_key_valid,
        is_tool_allowlisted=payload.is_tool_allowlisted,
        is_within_budget=payload.is_within_budget,
    )
