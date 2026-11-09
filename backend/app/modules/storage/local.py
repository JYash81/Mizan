"""Local filesystem implementation of StorageProvider with strict path traversal defenses."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from app.modules.storage.provider import (
    StorageBucket,
    StorageObjectMetadata,
    StorageObjectNotFoundError,
    StorageProvider,
    StorageSecurityError,
)


class LocalStorageProvider(StorageProvider):
    """Stores objects on the local filesystem under a root data-plane directory."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        # Ensure all defined buckets exist
        for b in StorageBucket:
            (self.root_dir / b.value).mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, bucket: str | StorageBucket, key: str) -> Path:
        bucket_str = bucket.value if isinstance(bucket, StorageBucket) else str(bucket)
        if "/" in bucket_str or "\\" in bucket_str or ".." in bucket_str:
            raise StorageSecurityError(f"Invalid bucket identifier: {bucket_str}")

        bucket_dir = (self.root_dir / bucket_str).resolve()
        # Clean leading slashes from key so Path joining doesn't reset to root
        clean_key = key.lstrip("/\\")
        target_path = (bucket_dir / clean_key).resolve()

        if not target_path.is_relative_to(bucket_dir):
            raise StorageSecurityError(f"Path traversal detected: {key}")

        return target_path

    def _meta_path(self, file_path: Path) -> Path:
        return file_path.with_name(file_path.name + ".mizan_meta")

    def put_object(
        self,
        bucket: str | StorageBucket,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> StorageObjectMetadata:
        target_path = self._resolve_safe_path(bucket, key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        sha256 = hashlib.sha256(data).hexdigest()
        now = datetime.now(UTC)

        # Atomic write via temporary file in the same directory
        temp_path = target_path.parent / f".tmp_{now.timestamp()}_{os.getpid()}_{target_path.name}"
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(target_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

        meta = StorageObjectMetadata(
            bucket=bucket.value if isinstance(bucket, StorageBucket) else str(bucket),
            key=key,
            size_bytes=len(data),
            content_type=content_type,
            sha256=sha256,
            created_at=now,
            etag=f'"{sha256[:16]}"',
        )

        # Write metadata companion file
        meta_dict = {
            "bucket": meta.bucket,
            "key": meta.key,
            "size_bytes": meta.size_bytes,
            "content_type": meta.content_type,
            "sha256": meta.sha256,
            "created_at": meta.created_at.isoformat(),
            "etag": meta.etag,
        }
        meta_temp = target_path.parent / f".tmp_meta_{now.timestamp()}_{target_path.name}"
        with open(meta_temp, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f)
            f.flush()
            os.fsync(f.fileno())
        meta_temp.replace(self._meta_path(target_path))

        return meta

    def get_object(
        self, bucket: str | StorageBucket, key: str
    ) -> tuple[bytes, StorageObjectMetadata]:
        target_path = self._resolve_safe_path(bucket, key)
        if not target_path.is_file():
            raise StorageObjectNotFoundError(f"Object not found: {bucket}/{key}")

        with open(target_path, "rb") as f:
            data = f.read()

        meta_path = self._meta_path(target_path)
        if meta_path.is_file():
            with open(meta_path, encoding="utf-8") as f:
                raw_meta = json.load(f)
            meta = StorageObjectMetadata(
                bucket=raw_meta["bucket"],
                key=raw_meta["key"],
                size_bytes=raw_meta["size_bytes"],
                content_type=raw_meta["content_type"],
                sha256=raw_meta["sha256"],
                created_at=datetime.fromisoformat(raw_meta["created_at"]),
                etag=raw_meta.get("etag"),
            )
        else:
            sha256 = hashlib.sha256(data).hexdigest()
            stat = target_path.stat()
            meta = StorageObjectMetadata(
                bucket=bucket.value if isinstance(bucket, StorageBucket) else str(bucket),
                key=key,
                size_bytes=len(data),
                content_type="application/octet-stream",
                sha256=sha256,
                created_at=datetime.fromtimestamp(stat.st_ctime, UTC),
                etag=f'"{sha256[:16]}"',
            )

        return data, meta

    def delete_object(self, bucket: str | StorageBucket, key: str) -> bool:
        target_path = self._resolve_safe_path(bucket, key)
        existed = False
        if target_path.is_file():
            target_path.unlink()
            existed = True
        meta_path = self._meta_path(target_path)
        if meta_path.is_file():
            meta_path.unlink()
        return existed

    def object_exists(self, bucket: str | StorageBucket, key: str) -> bool:
        target_path = self._resolve_safe_path(bucket, key)
        return target_path.is_file()

    def generate_download_url(
        self, bucket: str | StorageBucket, key: str, expires_in_seconds: int = 3600
    ) -> str:
        bucket_str = bucket.value if isinstance(bucket, StorageBucket) else str(bucket)
        # In local development, routes through local FastAPI download stream
        return f"/api/v1/storage/download/{bucket_str}/{key}"

    def list_objects(
        self, bucket: str | StorageBucket, prefix: str = ""
    ) -> list[StorageObjectMetadata]:
        bucket_str = bucket.value if isinstance(bucket, StorageBucket) else str(bucket)
        bucket_dir = self.root_dir / bucket_str
        if not bucket_dir.is_dir():
            return []

        results: list[StorageObjectMetadata] = []
        for path in bucket_dir.rglob("*"):
            if (
                path.is_file()
                and not path.name.endswith(".mizan_meta")
                and not path.name.startswith(".tmp_")
            ):
                rel_key = str(path.relative_to(bucket_dir)).replace("\\", "/")
                if rel_key.startswith(prefix):
                    try:
                        _, meta = self.get_object(bucket, rel_key)
                        results.append(meta)
                    except Exception:
                        continue
        return results
