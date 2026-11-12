"""Sentinel v2 & Security Governance Module."""

from app.modules.sentinel.act_enforcer import (
    execute_containment_order,
    verify_order_authenticity_and_scope,
)
from app.modules.sentinel.ai_security_guard import (
    AgentExecutionBudget,
    AISecurityViolationError,
    sanitize_retrieved_rag_content,
    validate_model_generated_sql,
    validate_tool_url_destination,
    validate_user_prompt,
)
from app.modules.sentinel.anti_rollback_service import (
    enforce_anti_rollback_floor,
    get_active_version_floor,
    publish_minimum_version_floor,
    validate_model_artifact_format,
)
from app.modules.sentinel.decide_service import (
    evaluate_and_issue_containment_order,
)
from app.modules.sentinel.detect_service import (
    ingest_security_event,
)
from app.modules.sentinel.exceptions import (
    AntiRollbackFloorViolationError,
    BlastRadiusLimitExceededError,
    ComponentBoundaryViolationError,
    DualApprovalRequiredError,
    EvidenceQuorumRequiredError,
    EvidenceSealedError,
    FailClosedTransferBlockedError,
    OrderExpiredError,
    OrderSignatureVerificationError,
    RecoveryIntegrityCheckFailedError,
    RecoveryQuorumError,
    ReplayedNonceError,
    SentinelError,
    SupportAccessDeniedError,
    SupportAccessExpiredError,
    TenantScopeMismatchError,
    UnsafeModelArtifactFormatError,
)
from app.modules.sentinel.fail_behaviour_matrix import (
    LocalEncryptedEventQueue,
    ProtectedOperation,
    evaluate_fail_behaviour,
)
from app.modules.sentinel.immutable_backup_service import (
    BackupRestoreError,
    BackupTamperError,
    ImmutableBackupStorage,
    backup_vault,
)
from app.modules.sentinel.key_governance_service import (
    KeyGovernanceRegistry,
    KeyHierarchyLayer,
    KeyRevokedError,
    key_registry,
)
from app.modules.sentinel.recovery_service import (
    approve_and_execute_sev1_recovery,
    initiate_sev1_recovery,
)
from app.modules.sentinel.regulatory_clocks import (
    check_and_escalate_unacknowledged_incidents,
    get_incident_regulatory_clock,
)
from app.modules.sentinel.sealed_evidence_vault import (
    purge_expired_evidence_records,
    seal_evidence,
    unseal_evidence_dual_approval,
)
from app.modules.sentinel.support_access_broker import (
    approve_support_access,
    list_support_requests,
    list_support_session_logs,
    request_support_access,
    revoke_support_access,
    verify_and_log_support_session,
)

__all__ = [
    "SentinelError",
    "OrderSignatureVerificationError",
    "OrderExpiredError",
    "ReplayedNonceError",
    "TenantScopeMismatchError",
    "BlastRadiusLimitExceededError",
    "DualApprovalRequiredError",
    "ComponentBoundaryViolationError",
    "AntiRollbackFloorViolationError",
    "UnsafeModelArtifactFormatError",
    "SupportAccessDeniedError",
    "SupportAccessExpiredError",
    "EvidenceSealedError",
    "EvidenceQuorumRequiredError",
    "FailClosedTransferBlockedError",
    "RecoveryQuorumError",
    "RecoveryIntegrityCheckFailedError",
    "evaluate_and_issue_containment_order",
    "execute_containment_order",
    "verify_order_authenticity_and_scope",
    "ingest_security_event",
    "evaluate_fail_behaviour",
    "ProtectedOperation",
    "LocalEncryptedEventQueue",
    "publish_minimum_version_floor",
    "get_active_version_floor",
    "enforce_anti_rollback_floor",
    "validate_model_artifact_format",
    "request_support_access",
    "approve_support_access",
    "verify_and_log_support_session",
    "revoke_support_access",
    "list_support_requests",
    "list_support_session_logs",
    "seal_evidence",
    "unseal_evidence_dual_approval",
    "purge_expired_evidence_records",
    "get_incident_regulatory_clock",
    "check_and_escalate_unacknowledged_incidents",
    "initiate_sev1_recovery",
    "approve_and_execute_sev1_recovery",
    "AISecurityViolationError",
    "validate_user_prompt",
    "sanitize_retrieved_rag_content",
    "validate_tool_url_destination",
    "validate_model_generated_sql",
    "AgentExecutionBudget",
    "KeyGovernanceRegistry",
    "KeyHierarchyLayer",
    "KeyRevokedError",
    "key_registry",
    "ImmutableBackupStorage",
    "backup_vault",
    "BackupTamperError",
    "BackupRestoreError",
]
