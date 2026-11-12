"""Sentinel v2 and Security Governance Exception Classes."""

from __future__ import annotations


class SentinelError(Exception):
    """Base exception for all Sentinel and Security Governance operations."""


class OrderSignatureVerificationError(SentinelError):
    """Raised when containment order signature is invalid or fails verification."""


class OrderExpiredError(SentinelError):
    """Raised when a containment order has passed its expiration timestamp."""


class ReplayedNonceError(SentinelError):
    """Raised when a containment order nonce has already been executed."""


class TenantScopeMismatchError(SentinelError):
    """Raised when an order or access request targets a mismatched tenant/workspace."""


class BlastRadiusLimitExceededError(SentinelError):
    """Raised when per-tenant containment actions exceed the rolling blast-radius window."""


class DualApprovalRequiredError(SentinelError):
    """Raised when cross-tenant action or restricted data access lacks two distinct approvers."""


class ComponentBoundaryViolationError(SentinelError):
    """Raised when a Sentinel component attempts an action outside its defined authority."""


class AntiRollbackFloorViolationError(SentinelError):
    """Raised when an attempted installation or rollback is below the signed minimum-version floor."""


class UnsafeModelArtifactFormatError(SentinelError):
    """Raised when an uploaded model artifact is in an executable or pickle-style unsafe format."""


class SupportAccessDeniedError(SentinelError):
    """Raised when access is requested without valid customer admin approval."""


class SupportAccessExpiredError(SentinelError):
    """Raised when support access credential has expired or been revoked."""


class EvidenceSealedError(SentinelError):
    """Raised when attempting to access sealed forensic evidence without authorization."""


class EvidenceQuorumRequiredError(SentinelError):
    """Raised when evidence unseal lacks two distinct authorized approvers."""


class FailClosedTransferBlockedError(SentinelError):
    """Raised when external data transfer fails closed under dependency outage."""


class RecoveryQuorumError(SentinelError):
    """Raised when Sev1 restoration lacks two distinct non-triggering approvers."""


class RecoveryIntegrityCheckFailedError(SentinelError):
    """Raised when pre-restoration integrity checks (credentials/policy/data) fail."""


class KeyRevokedError(SentinelError):
    """Raised when an operation attempts to use a revoked cryptographic key."""
