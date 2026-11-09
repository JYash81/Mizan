"""Domain exceptions for Milestone 13: Customer Runtime & Site Agent."""


class RuntimeDomainError(Exception):
    """Base exception for all customer runtime and site agent operations."""


class SiteNotFoundError(RuntimeDomainError):
    """Raised when a customer site cannot be found."""


class SiteSuspendedOrRevokedError(RuntimeDomainError):
    """Raised when attempting actions against a suspended or revoked customer site."""


class DuplicateSiteKeyError(RuntimeDomainError):
    """Raised when attempting to create a site with an already existing site key."""


class EnrollmentTokenExpiredError(RuntimeDomainError):
    """Raised when an enrollment token has passed its expiration time."""


class EnrollmentTokenAlreadyConsumedError(RuntimeDomainError):
    """Raised when an enrollment token has already been consumed."""


class InvalidEnrollmentTokenError(RuntimeDomainError):
    """Raised when an enrollment token is invalid, malformed, or has an incorrect hash."""


class AgentNotEnrolledError(RuntimeDomainError):
    """Raised when an operation requires an enrolled agent identity that does not exist."""


class AgentIdentityRevokedError(RuntimeDomainError):
    """Raised when an agent identity is revoked or invalid."""


class InvalidSignatureError(RuntimeDomainError):
    """Raised when an Ed25519 signature fails verification or has an unexpected purpose."""


class ExpiredCommandError(RuntimeDomainError):
    """Raised when a polled or submitted site agent command has expired."""


class ReplayedNonceError(RuntimeDomainError):
    """Raised when a site agent command nonce has already been seen or consumed."""


class UnallowlistedCommandError(RuntimeDomainError):
    """Raised when a command type is not in the strictly approved agent command allowlist."""


class PackageVerificationError(RuntimeDomainError):
    """Raised when package artifacts, checksums, or signatures fail validation."""


class PackageNotApprovedError(RuntimeDomainError):
    """Raised when attempting to deploy a model or app version that is not Gate 3 approved."""


class HardwarePreflightFailedError(RuntimeDomainError):
    """Raised when customer site hardware does not meet package runtime minimum requirements."""


class GoldenTestFailedError(RuntimeDomainError):
    """Raised when golden tests fail against a candidate slot, blocking activation."""


class SlotActivationBlockedError(RuntimeDomainError):
    """Raised when slot activation is rejected due to failed or missing golden tests."""


class SlotNotFoundError(RuntimeDomainError):
    """Raised when a requested blue/green runtime slot is not found."""


class InvalidSlotStateTransitionError(RuntimeDomainError):
    """Raised when an illegal blue/green slot transition is attempted."""


class InferenceEngineError(RuntimeDomainError):
    """Raised when local customer runtime inference fails."""


class SiteAccessDeniedError(RuntimeDomainError):
    """Raised when an actor lacks permission to manage a customer site or runtime slot."""
