"""Storage provider singleton factory."""

from functools import lru_cache

from app.core.config import get_settings
from app.modules.storage.local import LocalStorageProvider
from app.modules.storage.provider import StorageProvider
from app.modules.storage.s3 import S3StorageProvider

_override_storage_provider: StorageProvider | None = None


def set_storage_provider_override(provider: StorageProvider | None) -> None:
    global _override_storage_provider
    _override_storage_provider = provider


@lru_cache
def _get_default_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3StorageProvider(
            bucket_name=settings.storage_s3_bucket,
            endpoint_url=settings.storage_s3_endpoint_url,
            access_key=settings.storage_s3_access_key,
            secret_key=settings.storage_s3_secret_key,
            region=settings.storage_s3_region,
        )
    return LocalStorageProvider(root_dir=settings.storage_local_root)


def get_storage_provider() -> StorageProvider:
    """Returns the active storage provider (override or default)."""
    if _override_storage_provider is not None:
        return _override_storage_provider
    return _get_default_storage_provider()
