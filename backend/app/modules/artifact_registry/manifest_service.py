"""Canonical Release Manifest generator, validator, and SHA-256 digest engine for Milestone 11."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.artifact_registry import ModelVersion, RegisteredArtifact
from app.modules.masking.cryptography.signing_service import canonicalize_payload


def generate_release_manifest(
    model_version: ModelVersion,
    family_slug: str,
    artifacts: list[RegisteredArtifact],
    provenance_summary: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """Generate deterministic Release Manifest dictionary and SHA-256 digest.

    Invariants:
    1. Keys and sub-objects are strictly canonicalized.
    2. Artifacts are sorted deterministically by artifact_type and sha256.
    3. Output digest is reproducible across platforms.
    """
    sorted_artifacts = [
        {
            "artifact_type": art.artifact_type.value,
            "format": art.format,
            "quantization_type": art.quantization_type,
            "sha256": art.sha256,
            "file_size_bytes": art.file_size_bytes,
            "storage_reference": art.storage_reference,
            "is_primary_weights": art.is_primary_weights,
        }
        for art in sorted(artifacts, key=lambda a: (a.artifact_type.value, a.sha256))
    ]

    manifest_dict: dict[str, Any] = {
        "schema_version": "release-manifest-2026-11-09",
        "manifest_purpose": "RELEASE_MANIFEST",
        "model_version_id": model_version.id,
        "family_id": model_version.family_id,
        "family_slug": family_slug,
        "version_tag": model_version.version_tag,
        "source_model": {
            "model_key": model_version.source_model_key,
            "revision": model_version.source_model_revision,
        },
        "recipe_key": model_version.recipe_key,
        "build_provenance": {
            "build_run_id": model_version.build_run_id,
        },
        "dataset_provenance": {
            "dataset_id": model_version.dataset_id,
            "dataset_version_id": model_version.dataset_version_id,
            "dataset_version_digest": model_version.dataset_version_digest,
            "gate1_approval_id": model_version.gate1_approval_id,
        },
        "evaluation_metrics": {
            "base_evaluation_score": model_version.base_evaluation_score,
            "final_evaluation_score": model_version.final_evaluation_score,
            "quality_delta": model_version.quality_delta,
            "evaluation_run_id": model_version.evaluation_run_id,
        },
        "hardware_requirements": {
            "min_ram_mb": model_version.min_ram_mb,
            "min_vram_mb": model_version.min_vram_mb,
            "target_hardware_key": model_version.target_hardware_key,
        },
        "artifacts": sorted_artifacts,
        "provenance_verification": provenance_summary,
    }

    canonical_json = canonicalize_payload(manifest_dict)
    manifest_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return manifest_dict, manifest_digest


def verify_release_manifest_integrity(
    manifest_json_or_dict: str | dict[str, Any],
    expected_digest: str,
) -> bool:
    """Verify that a release manifest string or dictionary exactly matches its expected SHA-256 digest."""
    if isinstance(manifest_json_or_dict, str):
        try:
            payload = json.loads(manifest_json_or_dict)
        except Exception:
            return False
    else:
        payload = manifest_json_or_dict

    canonical_json = canonicalize_payload(payload)
    calculated_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return calculated_digest.lower() == expected_digest.lower()
