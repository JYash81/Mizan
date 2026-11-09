"""Regression tests for M15 Encrypted Backup & Key Recovery Manager."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.backup_manager import (
    BACKUP_MAGIC_HEADER,
    BackupDecryptionError,
    BackupIntegrityError,
    BackupSecurityError,
    create_encrypted_backup,
    verify_and_restore_backup,
)


@pytest.fixture
def sample_backup_source(tmp_path: Path) -> Path:
    """Create a temporary directory containing synthetic state and an Ed25519 key."""
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True)

    # 1. Synthetic SQLite DB file
    db_file = source_dir / "mizan_test.db"
    db_file.write_bytes(b"SQLite format 3\x00" + b"\x00" * 4096)

    # 2. Synthetic Ed25519 Private Key
    keys_dir = source_dir / "keys"
    keys_dir.mkdir()
    priv_key = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_file = keys_dir / "synthetic-test-01.key"
    key_file.write_bytes(priv_pem)

    # 3. Synthetic Data Plane file
    data_file = source_dir / "dataset.json"
    data_file.write_text('{"records": 100}', encoding="utf-8")

    return source_dir


def test_backup_encryption_and_restoration_cycle(sample_backup_source: Path, tmp_path: Path):
    """Test full backup, encryption, verification, and restoration lifecycle."""
    backup_file = tmp_path / "mizan_backup.enc"
    restore_dir = tmp_path / "restored"
    passphrase = "SuperSecretBackupPassphrase2026!"

    # 1. Create encrypted backup
    manifest = create_encrypted_backup(sample_backup_source, backup_file, passphrase)
    assert backup_file.exists()
    assert manifest.files_count == 3
    assert manifest.cipher_algorithm == "AES-256-GCM"

    # Confirm the encrypted file cannot be opened as a plain ZIP
    with pytest.raises(zipfile.BadZipFile):
        with zipfile.ZipFile(backup_file, "r") as zf:
            zf.namelist()

    # Confirm raw private key bytes do not appear in ciphertext
    ciphertext = backup_file.read_bytes()
    assert b"BEGIN PRIVATE KEY" not in ciphertext

    # 2. Restore backup with correct passphrase
    result = verify_and_restore_backup(backup_file, restore_dir, passphrase, manifest)
    assert result.restored_files_count == 3

    # Verify restored key is valid
    restored_key_file = restore_dir / "keys" / "synthetic-test-01.key"
    assert restored_key_file.exists()
    restored_pem = restored_key_file.read_bytes()
    loaded_key = serialization.load_pem_private_key(restored_pem, password=None)
    assert isinstance(loaded_key, ed25519.Ed25519PrivateKey)


def test_backup_invalid_passphrase_rejected(sample_backup_source: Path, tmp_path: Path):
    """Attempting restoration with the wrong passphrase must raise BackupDecryptionError."""
    backup_file = tmp_path / "mizan_backup.enc"
    restore_dir = tmp_path / "restored"
    passphrase = "SuperSecretBackupPassphrase2026!"

    manifest = create_encrypted_backup(sample_backup_source, backup_file, passphrase)

    with pytest.raises(BackupDecryptionError, match="Authentication failed"):
        verify_and_restore_backup(backup_file, restore_dir, "WrongPassphrase123!", manifest)


def test_backup_tampered_ciphertext_rejected(sample_backup_source: Path, tmp_path: Path):
    """Tampering with a single byte of ciphertext must fail decryption."""
    backup_file = tmp_path / "mizan_backup.enc"
    restore_dir = tmp_path / "restored"
    passphrase = "SuperSecretBackupPassphrase2026!"

    manifest = create_encrypted_backup(sample_backup_source, backup_file, passphrase)

    # Corrupt a byte in the ciphertext payload
    data = bytearray(backup_file.read_bytes())
    data[-5] ^= 0xFF
    backup_file.write_bytes(data)

    # Manifest check fails first if expected_manifest is provided
    with pytest.raises(BackupIntegrityError, match="Backup SHA-256 mismatch"):
        verify_and_restore_backup(backup_file, restore_dir, passphrase, manifest)

    # Even without manifest check, AES-GCM tag verification must fail
    with pytest.raises(BackupDecryptionError, match="Authentication failed"):
        verify_and_restore_backup(backup_file, restore_dir, passphrase, expected_manifest=None)


def test_backup_path_traversal_zip_slip_rejected(tmp_path: Path):
    """Malicious archive with Zip Slip directory traversal must be rejected."""
    # Construct a synthetic encrypted payload containing ../ malicious path
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")

    malicious_plaintext = zip_buf.getvalue()

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from app.core.backup_manager import _derive_key

    salt = b"0" * 16
    nonce = b"1" * 12
    key = _derive_key("testpass123", salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, malicious_plaintext, BACKUP_MAGIC_HEADER)

    evil_backup = tmp_path / "evil_backup.enc"
    with open(evil_backup, "wb") as f:
        f.write(BACKUP_MAGIC_HEADER + salt + nonce + ciphertext)

    restore_dir = tmp_path / "target"
    with pytest.raises(BackupSecurityError, match="Path traversal detected"):
        verify_and_restore_backup(evil_backup, restore_dir, "testpass123")
