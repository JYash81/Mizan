"""Tests for Mizan storage provider abstraction and local implementation."""

import tempfile
from pathlib import Path

import pytest

from app.modules.storage import (
    LocalStorageProvider,
    StorageBucket,
    StorageObjectNotFoundError,
    StorageSecurityError,
)


@pytest.fixture
def temp_storage_root():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_local_storage_put_and_get(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    bucket = StorageBucket.RAW_UPLOADS
    key = "tenant_123/documents/sample.txt"
    payload = b"Hello, Mizan Sovereign Storage!"

    meta = provider.put_object(bucket, key, payload, content_type="text/plain")

    assert meta.bucket == StorageBucket.RAW_UPLOADS.value
    assert meta.key == key
    assert meta.size_bytes == len(payload)
    assert meta.content_type == "text/plain"
    assert len(meta.sha256) == 64

    data, read_meta = provider.get_object(bucket, key)
    assert data == payload
    assert read_meta.sha256 == meta.sha256
    assert read_meta.size_bytes == len(payload)
    assert read_meta.content_type == "text/plain"


def test_local_storage_delete_and_exists(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    bucket = StorageBucket.RAW_UPLOADS
    key = "tenant_123/documents/to_delete.txt"
    payload = b"Disposable data"

    assert not provider.object_exists(bucket, key)
    provider.put_object(bucket, key, payload)
    assert provider.object_exists(bucket, key)

    deleted = provider.delete_object(bucket, key)
    assert deleted is True
    assert not provider.object_exists(bucket, key)

    deleted_again = provider.delete_object(bucket, key)
    assert deleted_again is False


def test_local_storage_not_found(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    with pytest.raises(StorageObjectNotFoundError):
        provider.get_object(StorageBucket.RAW_UPLOADS, "nonexistent/file.bin")


def test_local_storage_path_traversal_prevention(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    bucket = StorageBucket.RAW_UPLOADS

    malicious_keys = [
        "../../etc/passwd",
        "../sibling_bucket/file.txt",
        "valid/../../outside.txt",
        "..\\..\\windows\\system32\\calc.exe",
    ]

    for key in malicious_keys:
        with pytest.raises(StorageSecurityError):
            provider.put_object(bucket, key, b"attack payload")

        with pytest.raises(StorageSecurityError):
            provider.get_object(bucket, key)

        with pytest.raises(StorageSecurityError):
            provider.delete_object(bucket, key)


def test_local_storage_invalid_bucket(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    with pytest.raises(StorageSecurityError):
        provider.put_object("../sneaky_bucket", "file.txt", b"payload")


def test_local_storage_list_objects(temp_storage_root):
    provider = LocalStorageProvider(temp_storage_root)
    bucket = StorageBucket.RAW_UPLOADS

    provider.put_object(bucket, "ws_1/doc_1.txt", b"1")
    provider.put_object(bucket, "ws_1/doc_2.txt", b"22")
    provider.put_object(bucket, "ws_2/doc_3.txt", b"333")

    ws1_items = provider.list_objects(bucket, prefix="ws_1/")
    assert len(ws1_items) == 2
    keys = {item.key for item in ws1_items}
    assert keys == {"ws_1/doc_1.txt", "ws_1/doc_2.txt"}
