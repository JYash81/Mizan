"""Mizan Enterprise Encrypted Backup and Disaster Recovery Manager.

Provides authenticated symmetric encryption (AES-256-GCM) with PBKDF2-HMAC-SHA256
key derivation for cold backups, ensuring private signing keys and database state
are never exposed in plaintext backup archives.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BACKUP_MAGIC_HEADER = b"MIZANENC"
KDF_ITERATIONS = 600_000
SALT_SIZE_BYTES = 16
NONCE_SIZE_BYTES = 12


class BackupError(Exception):
    """Base backup and disaster recovery error."""


class BackupDecryptionError(BackupError):
    """Raised when decryption fails due to invalid secret or corrupted ciphertext."""


class BackupIntegrityError(BackupError):
    """Raised when backup manifest checksum fails or payload is tampered."""


class BackupSecurityError(BackupError):
    """Raised when an archive attempts path traversal or unsafe extraction."""


@dataclass(frozen=True)
class BackupManifest:
    archive_name: str
    sha256: str
    unencrypted_size_bytes: int
    encrypted_size_bytes: int
    created_at_utc: float
    files_count: int
    kdf_algorithm: str = "PBKDF2-HMAC-SHA256"
    kdf_iterations: int = KDF_ITERATIONS
    cipher_algorithm: str = "AES-256-GCM"


@dataclass(frozen=True)
class RestoreResult:
    restored_files_count: int
    total_restored_bytes: int
    elapsed_seconds: float
    target_directory: str


def compute_file_sha256(filepath: Path) -> str:
    """Compute streaming SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit symmetric key from passphrase and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def create_encrypted_backup(
    source_dir: Path,
    output_encrypted_path: Path,
    passphrase: str,
) -> BackupManifest:
    """Pack source directory into memory and encrypt with AES-256-GCM.

    Format:
    [8 bytes MAGIC: MIZANENC]
    [16 bytes SALT]
    [12 bytes NONCE]
    [CIPHERTEXT + 16 bytes AUTH TAG]
    """
    if not passphrase or len(passphrase) < 8:
        raise BackupSecurityError("Backup passphrase must be at least 8 characters.")

    source_dir = Path(source_dir).resolve()
    if not source_dir.exists():
        raise BackupError(f"Source directory does not exist: {source_dir}")

    # Pack files into an in-memory zip
    zip_buffer = io.BytesIO()
    files_count = 0
    unencrypted_bytes = 0

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(source_dir)
                zf.write(file_path, arcname=str(rel_path))
                files_count += 1
                unencrypted_bytes += file_path.stat().st_size

    plaintext_data = zip_buffer.getvalue()

    # Generate cryptographic parameters
    salt = os.urandom(SALT_SIZE_BYTES)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    derived_key = _derive_key(passphrase, salt)

    aesgcm = AESGCM(derived_key)
    # Additional authenticated data binds magic header to ciphertext
    ciphertext = aesgcm.encrypt(nonce, plaintext_data, BACKUP_MAGIC_HEADER)

    output_encrypted_path = Path(output_encrypted_path).resolve()
    output_encrypted_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_encrypted_path, "wb") as f:
        f.write(BACKUP_MAGIC_HEADER)
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)

    manifest = BackupManifest(
        archive_name=output_encrypted_path.name,
        sha256=compute_file_sha256(output_encrypted_path),
        unencrypted_size_bytes=unencrypted_bytes,
        encrypted_size_bytes=output_encrypted_path.stat().st_size,
        created_at_utc=time.time(),
        files_count=files_count,
    )

    # Save manifest next to backup
    manifest_path = output_encrypted_path.with_suffix(".manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, indent=2)

    return manifest


def verify_and_restore_backup(
    encrypted_backup_path: Path,
    target_dir: Path,
    passphrase: str,
    expected_manifest: BackupManifest | dict | None = None,
) -> RestoreResult:
    """Verify integrity and decrypt AES-256-GCM backup archive into target directory."""
    start_time = time.perf_counter()
    encrypted_backup_path = Path(encrypted_backup_path).resolve()
    target_dir = Path(target_dir).resolve()

    if not encrypted_backup_path.exists():
        raise BackupError(f"Backup file does not exist: {encrypted_backup_path}")

    # 1. Manifest SHA-256 verification (if provided)
    if expected_manifest:
        expected_sha = (
            expected_manifest.sha256
            if isinstance(expected_manifest, BackupManifest)
            else expected_manifest.get("sha256")
        )
        actual_sha = compute_file_sha256(encrypted_backup_path)
        if actual_sha != expected_sha:
            raise BackupIntegrityError(
                f"Backup SHA-256 mismatch! Expected {expected_sha}, got {actual_sha}."
            )

    # 2. Read and parse binary structure
    with open(encrypted_backup_path, "rb") as f:
        magic = f.read(len(BACKUP_MAGIC_HEADER))
        if magic != BACKUP_MAGIC_HEADER:
            raise BackupIntegrityError("File is not a valid encrypted Mizan backup.")

        salt = f.read(SALT_SIZE_BYTES)
        nonce = f.read(NONCE_SIZE_BYTES)
        ciphertext = f.read()

    # 3. Key derivation and decryption
    derived_key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(derived_key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, BACKUP_MAGIC_HEADER)
    except InvalidTag as err:
        raise BackupDecryptionError(
            "Authentication failed: Invalid backup passphrase or tampered ciphertext."
        ) from err

    # 4. Safe ZIP extraction with Path Traversal / Zip Slip protection
    zip_buffer = io.BytesIO(plaintext)
    target_dir.mkdir(parents=True, exist_ok=True)
    restored_count = 0
    total_bytes = 0

    with zipfile.ZipFile(zip_buffer, mode="r") as zf:
        for member in zf.infolist():
            member_path = Path(member.filename)
            dest_path = (target_dir / member_path).resolve()

            # Path traversal verification
            if not dest_path.is_relative_to(target_dir):
                raise BackupSecurityError(
                    f"Path traversal detected in archive member: {member.filename}"
                )

            if member.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source_file, open(dest_path, "wb") as target_file:
                    shutil.copyfileobj(source_file, target_file)

                # Set restrictive file permissions for private keys and databases
                if dest_path.suffix in (".key", ".pem"):
                    try:
                        dest_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
                    except OSError:
                        pass  # Windows permissions handled by default ACLs

                restored_count += 1
                total_bytes += dest_path.stat().st_size

    elapsed = time.perf_counter() - start_time
    return RestoreResult(
        restored_files_count=restored_count,
        total_restored_bytes=total_bytes,
        elapsed_seconds=elapsed,
        target_directory=str(target_dir),
    )
