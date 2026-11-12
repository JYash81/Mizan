"""Anti-Rollback Signed Minimum-Version Floor & Safe Model Format Validation.

Implements Section 8 of Mizan Security Strategy v2:
- Runtimes verify signed minimum-version floor: packages below the floor are rejected even if validly signed.
- Models must use non-executable formats (safetensors, gguf, json, onnx). Pickle-style and executable formats are rejected.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.sentinel import SignedVersionFloor
from app.modules.masking.cryptography.signing_service import (
    canonicalize_payload,
    get_public_key,
    sign_payload,
    verify_signature,
)
from app.modules.sentinel.exceptions import (
    AntiRollbackFloorViolationError,
    UnsafeModelArtifactFormatError,
)
from app.modules.sentinel.schemas import SignedVersionFloorRead

VERSION_FLOOR_KEY_ID = "sentinel_version_floor_key"
VERSION_FLOOR_PURPOSE = "VERSION_FLOOR_SIGNING"

ALLOWED_MODEL_EXTENSIONS = {".safetensors", ".gguf", ".json", ".onnx"}
PROHIBITED_MODEL_EXTENSIONS = {
    ".pkl",
    ".pickle",
    ".pt",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".sh",
    ".bat",
    ".py",
}


def _parse_semver(version: str) -> tuple[int, int, int]:
    """Parses semantic version 'X.Y.Z' into integer tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid semantic version string: '{version}'")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def publish_minimum_version_floor(
    db: Session,
    minimum_version: str,
    workspace_id: str | None = None,
) -> SignedVersionFloorRead:
    """Signs and distributes a new minimum-version floor."""
    _parse_semver(minimum_version)  # Validate format
    now = datetime.now(UTC)
    nonce = secrets.token_hex(16)

    canonical_payload = {
        "effective_at": now.isoformat(),
        "minimum_version": minimum_version,
        "nonce": nonce,
        "purpose": VERSION_FLOOR_PURPOSE,
        "workspace_id": workspace_id or "GLOBAL",
    }

    canonical_str, signature_hex, signer_key = sign_payload(
        canonical_payload, key_id=VERSION_FLOOR_KEY_ID
    )
    pub_key = get_public_key(VERSION_FLOOR_KEY_ID)
    from cryptography.hazmat.primitives import serialization

    pub_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    floor = SignedVersionFloor(
        workspace_id=workspace_id,
        minimum_version=minimum_version,
        effective_at=now,
        nonce=nonce,
        signature=signature_hex,
        canonical_payload=canonical_str,
        signer_public_key=pub_bytes.decode("utf-8"),
    )
    db.add(floor)
    db.commit()
    db.refresh(floor)

    return SignedVersionFloorRead.model_validate(floor)


def get_active_version_floor(
    db: Session,
    workspace_id: str | None = None,
) -> SignedVersionFloorRead | None:
    """Retrieves the latest signed minimum-version floor."""
    query = select(SignedVersionFloor).order_by(desc(SignedVersionFloor.effective_at))
    if workspace_id:
        query = query.where(
            (SignedVersionFloor.workspace_id == workspace_id)
            | (SignedVersionFloor.workspace_id.is_(None))
        )
    floor = db.execute(query).scalars().first()
    if not floor:
        return None
    return SignedVersionFloorRead.model_validate(floor)


def enforce_anti_rollback_floor(
    db: Session,
    target_version: str,
    workspace_id: str | None = None,
) -> None:
    """Enforces that target package version is at or above the signed floor.

    Raises:
        AntiRollbackFloorViolationError: If target_version < floor_version.
    """
    floor = get_active_version_floor(db, workspace_id)
    if not floor:
        return  # No floor configured

    # Verify signature of the floor record
    if floor.canonical_payload:
        canonical_str = floor.canonical_payload
    else:
        canonical_data = {
            "effective_at": floor.effective_at.isoformat(),
            "minimum_version": floor.minimum_version,
            "nonce": floor.nonce,
            "purpose": VERSION_FLOOR_PURPOSE,
            "workspace_id": floor.workspace_id or "GLOBAL",
        }
        canonical_str = canonicalize_payload(canonical_data)
    verify_signature(canonical_str, floor.signature, VERSION_FLOOR_KEY_ID)

    target_tuple = _parse_semver(target_version)
    floor_tuple = _parse_semver(floor.minimum_version)

    if target_tuple < floor_tuple:
        raise AntiRollbackFloorViolationError(
            f"Package version '{target_version}' is below the signed minimum-version floor "
            f"'{floor.minimum_version}'. Installation or rollback rejected."
        )


def validate_model_artifact_format(filename: str, content: bytes) -> None:
    """Verifies model artifact format is non-executable and safe.

    Raises:
        UnsafeModelArtifactFormatError: If format is pickle, executable, or prohibited.
    """
    lower_name = filename.lower()
    ext = "." + lower_name.split(".")[-1] if "." in lower_name else ""

    # Check extension
    if ext in PROHIBITED_MODEL_EXTENSIONS or "pytorch_model.bin" in lower_name:
        raise UnsafeModelArtifactFormatError(
            f"Model artifact '{filename}' uses prohibited/unsafe format '{ext}'. "
            "Executable and pickle-based weights are rejected; use safetensors or gguf."
        )

    # Magic byte inspection
    if len(content) >= 2:
        # Python pickle protocol 2..5 magic opcode starts with 0x80 followed by protocol number
        if content[0] == 0x80 and content[1] in (0x02, 0x03, 0x04, 0x05):
            raise UnsafeModelArtifactFormatError(
                f"Model artifact '{filename}' contains pickle magic bytes (0x80). Rejected."
            )
        # Windows PE executable magic 'MZ'
        if content[:2] == b"MZ":
            raise UnsafeModelArtifactFormatError(
                f"Model artifact '{filename}' is a Windows executable binary. Rejected."
            )
        # Linux ELF magic '\x7fELF'
        if content[:4] == b"\x7fELF":
            raise UnsafeModelArtifactFormatError(
                f"Model artifact '{filename}' is a Linux executable binary. Rejected."
            )

    # Extension must be in approved allowlist
    if ext not in ALLOWED_MODEL_EXTENSIONS:
        raise UnsafeModelArtifactFormatError(
            f"Model artifact '{filename}' has unsupported extension '{ext}'. "
            f"Permitted formats: {sorted(ALLOWED_MODEL_EXTENSIONS)}"
        )
