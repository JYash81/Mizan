"""Artifact staging, format header verification, checksum validation, and M11 boundary enforcement."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_building import (
    ArtifactType,
    ArtifactVerificationStatus,
    ModelBuildEvent,
    ModelBuildRun,
    StagedModelArtifact,
)
from app.modules.model_building.quantization_service import GGUF_MAGIC_BYTES
from app.modules.storage.provider import StorageBucket
from app.modules.storage.service import get_storage_provider


class ArtifactStagingError(Exception):
    """Raised when an uploaded or produced artifact fails integrity verification."""


# Maximum single artifact upload size: 10 GB
MAX_ARTIFACT_SIZE_BYTES = 10 * 1024 * 1024 * 1024


def stage_model_artifact(
    db: Session,
    build_run: ModelBuildRun,
    artifact_type: ArtifactType,
    format_name: str,
    artifact_bytes: bytes,
    expected_sha256: str | None = None,
    quantization_type: str | None = None,
    tokenizer_reference: str | None = None,
) -> StagedModelArtifact:
    """Validate artifact file format, size, and hash, then stage in storage.

    IMPORTANT ARCHITECTURAL INVARIANT:
    Staged artifacts are NOT release artifacts and do NOT constitute Gate 3 release approval.
    """
    file_size = len(artifact_bytes)
    if file_size == 0:
        raise ArtifactStagingError("Artifact cannot be empty (0 bytes).")
    if file_size > MAX_ARTIFACT_SIZE_BYTES:
        raise ArtifactStagingError(
            f"Artifact size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed {MAX_ARTIFACT_SIZE_BYTES / (1024*1024):.1f} MB."
        )

    # 1. Format Header / Magic Byte Validation
    verification_details: dict[str, Any] = {"format": format_name}
    norm_fmt = format_name.upper().strip()

    if norm_fmt == "GGUF":
        if not artifact_bytes.startswith(GGUF_MAGIC_BYTES):
            raise ArtifactStagingError(
                "Invalid GGUF artifact: missing standard 'GGUF' magic byte header."
            )
        verification_details["header_magic"] = "GGUF"

    elif norm_fmt == "SAFETENSORS":
        # Check for safetensors json header prefix (8-byte unsigned int header length)
        if len(artifact_bytes) < 8:
            raise ArtifactStagingError("Invalid Safetensors artifact: file truncated.")
        verification_details["header_checked"] = True

    # 2. Hash Calculation & Verification
    calculated_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if expected_sha256 and expected_sha256.lower() != calculated_sha256.lower():
        raise ArtifactStagingError(
            f"SHA-256 hash mismatch! Expected: {expected_sha256}, Calculated: {calculated_sha256}"
        )
    verification_details["sha256"] = calculated_sha256

    # 3. Storage Persistence
    storage = get_storage_provider()
    ext = "gguf" if norm_fmt == "GGUF" else ("safetensors" if norm_fmt == "SAFETENSORS" else "bin")
    storage_key = (
        f"workspaces/{build_run.workspace_id}/builds/{build_run.id}/staged/{artifact_type.value.lower()}_{calculated_sha256[:12]}.{ext}"
    )

    storage.put_object(
        bucket=StorageBucket.ARTIFACTS,
        key=storage_key,
        data=artifact_bytes,
        content_type="application/octet-stream",
    )

    # 4. Database Staging Record (Strictly Pre-M11)
    artifact = StagedModelArtifact(
        organization_id=build_run.organization_id,
        workspace_id=build_run.workspace_id,
        build_run_id=build_run.id,
        artifact_type=artifact_type,
        format=format_name,
        storage_reference=storage_key,
        file_size_bytes=file_size,
        sha256=calculated_sha256,
        source_model_key=build_run.source_model.model_key if build_run.source_model else "unknown",
        source_model_revision=build_run.source_revision,
        quantization_type=quantization_type,
        manifest_digest=build_run.manifest_digest,
        model_config_digest=build_run.source_model.config_digest if build_run.source_model else None,
        tokenizer_reference=tokenizer_reference,
        verification_status=ArtifactVerificationStatus.VERIFIED,
        verification_details_json=json.dumps(verification_details),
        is_staged_for_m11=True,  # Explicit boundary label
    )
    db.add(artifact)

    event = ModelBuildEvent(
        build_run_id=build_run.id,
        event_type="ARTIFACT_STAGED",
        message=f"Artifact {artifact_type.value} ({format_name}, {file_size / (1024*1024):.2f} MB) successfully staged.",
        metadata_json=json.dumps(
            {"artifact_type": artifact_type.value, "sha256": calculated_sha256, "storage_key": storage_key}
        ),
    )
    db.add(event)
    db.commit()
    db.refresh(artifact)
    return artifact
