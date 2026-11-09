"""Domain exceptions for Milestone 12: Model Zoo, App Zoo, and Enterprise Catalog."""


class CatalogError(Exception):
    """Base exception for all catalog domain errors."""


class ListingNotFoundError(CatalogError):
    """Raised when a catalog listing cannot be found."""


class ListingNotPublishedError(CatalogError):
    """Raised when accessing a non-published listing through public/discovery channels."""


class UnapprovedReleaseError(CatalogError):
    """Raised when attempting to list or bind an unapproved M11 model version."""


class RevokedReleaseError(CatalogError):
    """Raised when attempting to list, publish, or download a revoked M11 model release."""


class LicenseRestrictionError(CatalogError):
    """Raised when license restrictions prohibit publication or redistribution."""


class DownloadNotPermittedError(CatalogError):
    """Raised when download is prohibited (e.g. metadata-only listing or restricted distribution)."""


class PublicPublicationNotAllowedError(CatalogError):
    """Raised when a listing cannot be published publicly due to unverified rights or data disclosure."""


class DependencyRevocationError(CatalogError):
    """Raised when an application dependency references a revoked or unapproved model version."""


class InvalidManifestError(CatalogError):
    """Raised when an application manifest is invalid or malformed."""


class ListingReviewError(CatalogError):
    """Raised when a listing review action violates governance policies."""
