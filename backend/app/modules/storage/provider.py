"""Storage provider interface, metadata, and bucket definitions for Mizan."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StorageBucket(StrEnum):
    RAW_UPLOADS = "raw_uploads"
    MASKED_DATASETS = "masked_datasets"
    EVALUATIONS = "evaluations"
    ARTIFACTS = "artifacts"
    RELEASES = "releases"
    CUSTOMER_PACKAGES = "customer_packages"


class StorageError(Exception):
    """Base storage exception."""


class StorageObjectNotFoundError(StorageError):
    """Raised when an object does not exist in storage."""


class StorageSecurityError(StorageError):
    """Raised when a storage path or key violates security boundaries."""


@dataclass(frozen=True)
class StorageObjectMetadata:
    bucket: str
    key: str
    size_bytes: int
    content_type: str
    sha256: str
    created_at: datetime
    etag: str | None = None


class StorageProvider(ABC):
    """Abstract interface for all Mizan storage backends."""

    @abstractmethod
    def put_object(
        self,
        bucket: str | StorageBucket,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> StorageObjectMetadata:
        """Write bytes to storage atomically and return metadata."""

    @abstractmethod
    def get_object(
        self, bucket: str | StorageBucket, key: str
    ) -> tuple[bytes, StorageObjectMetadata]:
        """Read bytes and metadata for an object. Raises StorageObjectNotFoundError if missing."""

    @abstractmethod
    def delete_object(self, bucket: str | StorageBucket, key: str) -> bool:
        """Delete an object. Returns True if deleted, False if it did not exist."""

    @abstractmethod
    def object_exists(self, bucket: str | StorageBucket, key: str) -> bool:
        """Check if an object exists."""

    @abstractmethod
    def generate_download_url(
        self, bucket: str | StorageBucket, key: str, expires_in_seconds: int = 3600
    ) -> str:
        """Generate a short-lived download URL or token-authorized route."""

    @abstractmethod
    def list_objects(
        self, bucket: str | StorageBucket, prefix: str = ""
    ) -> list[StorageObjectMetadata]:
        """List objects matching a prefix."""
