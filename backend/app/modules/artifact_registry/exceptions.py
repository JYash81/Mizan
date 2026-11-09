"""Exceptions for Milestone 11 Artifact Registry and Gate 3 Release Management."""

from __future__ import annotations


class ArtifactRegistryError(Exception):
    """Base exception for Artifact Registry operations."""

    def __init__(self, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ImmutableReleaseError(ArtifactRegistryError):
    """Raised when an operation attempts to modify an approved or finalized release."""

    def __init__(self, message: str = "Approved model versions and their registered artifacts are immutable."):
        super().__init__(message=message, status_code=409, details={"reason": "IMMUTABLE_RELEASE"})


class ReleaseNotFoundError(ArtifactRegistryError):
    """Raised when a requested model family, version, or artifact is not found."""

    def __init__(self, message: str = "Requested model family or version not found."):
        super().__init__(message=message, status_code=404, details={"reason": "NOT_FOUND"})


class ProvenanceVerificationError(ArtifactRegistryError):
    """Raised when model provenance verification fails required release criteria."""

    def __init__(self, message: str, blockers: list[str] | None = None):
        super().__init__(
            message=message,
            status_code=422,
            details={"reason": "PROVENANCE_VERIFICATION_FAILED", "blockers": blockers or []},
        )


class Gate3ApprovalError(ArtifactRegistryError):
    """Raised when Gate 3 human approval workflow encounters a policy or signature violation."""

    def __init__(self, message: str, status_code: int = 400, details: dict | None = None):
        super().__init__(message=message, status_code=status_code, details=details or {"reason": "GATE3_ERROR"})


class SeparationOfDutiesViolationError(Gate3ApprovalError):
    """Raised when a release creator attempts to approve their own release under strict governance."""

    def __init__(
        self,
        message: str = "Separation of duties violation: The model version creator cannot approve Gate 3 release.",
    ):
        super().__init__(
            message=message,
            status_code=403,
            details={"reason": "SEPARATION_OF_DUTIES_VIOLATION"},
        )


class SignaturePurposeMismatchError(Gate3ApprovalError):
    """Raised when an Ed25519 signature from Gate 1 or Gate 2 is presented for Gate 3."""

    def __init__(
        self,
        message: str = "Invalid signature purpose: Gate 1 and Gate 2 attestations cannot substitute for Gate 3 approval.",
    ):
        super().__init__(
            message=message,
            status_code=403,
            details={"reason": "SIGNATURE_PURPOSE_MISMATCH"},
        )
