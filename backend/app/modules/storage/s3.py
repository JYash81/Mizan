"""S3 / Cloudflare R2 storage provider adapter."""

from app.modules.storage.provider import (
    StorageBucket,
    StorageError,
    StorageObjectMetadata,
    StorageProvider,
)


class S3StorageProvider(StorageProvider):
    """Storage provider for AWS S3 and S3-compatible APIs (Cloudflare R2, MinIO)."""

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "auto",
    ) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

        if not self.bucket_name or not self.access_key or not self.secret_key:
            self._configured = False
        else:
            self._configured = True

    def _check_configured(self) -> None:
        if not self._configured:
            raise StorageError(
                "S3StorageProvider is not fully configured with bucket, access_key, and secret_key."
            )

    def put_object(
        self,
        bucket: str | StorageBucket,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> StorageObjectMetadata:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")

    def get_object(
        self, bucket: str | StorageBucket, key: str
    ) -> tuple[bytes, StorageObjectMetadata]:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")

    def delete_object(self, bucket: str | StorageBucket, key: str) -> bool:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")

    def object_exists(self, bucket: str | StorageBucket, key: str) -> bool:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")

    def generate_download_url(
        self, bucket: str | StorageBucket, key: str, expires_in_seconds: int = 3600
    ) -> str:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")

    def list_objects(
        self, bucket: str | StorageBucket, prefix: str = ""
    ) -> list[StorageObjectMetadata]:
        self._check_configured()
        raise NotImplementedError("Production S3 client integration requires boto3 credentials.")
