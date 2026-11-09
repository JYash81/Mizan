"""Deterministic RFC 8785 canonical manifest generation and SHA-256 digest calculation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.model_building import ModelBuildRecipe, ModelSource


def canonical_json_dumps(obj: Any) -> str:
    """Format a Python object into canonical JSON with sorted keys and compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_build_manifest(
    model: ModelSource,
    recipe: ModelBuildRecipe,
    training_config: dict[str, Any],
    dataset_metadata: dict[str, Any] | None = None,
    preflight_metadata: dict[str, Any] | None = None,
    recommendation_metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """Construct an immutable canonical build manifest and its SHA-256 digest.

    Returns:
        (manifest_dict, manifest_digest)
    """
    # Sanitize config: remove any accidental tokens or passwords
    sanitized_config = {
        k: v
        for k, v in training_config.items()
        if not any(secret_kw in k.lower() for secret_kw in ["token", "secret", "password", "key"])
    }

    manifest: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "source_model": {
            "model_key": model.model_key,
            "name": model.name,
            "architecture": model.architecture,
            "immutable_revision": model.immutable_revision,
            "parameter_count_millions": model.parameter_count_millions,
            "context_length": model.context_length,
            "tokenizer_digest": model.tokenizer_digest,
            "config_digest": model.config_digest,
            "license_id": model.license_id,
        },
        "recipe": {
            "recipe_key": recipe.recipe_key,
            "recipe_version": recipe.recipe_version,
            "recipe_type": recipe.recipe_type.value,
            "dependency_lock": recipe.dependency_lock,
            "training_config": sanitized_config,
        },
        "dataset": {
            "dataset_id": dataset_metadata.get("dataset_id") if dataset_metadata else None,
            "dataset_version_id": dataset_metadata.get("version_id") if dataset_metadata else None,
            "dataset_version_digest": dataset_metadata.get("version_digest") if dataset_metadata else None,
            "gate1_approval_id": dataset_metadata.get("gate1_approval_id") if dataset_metadata else None,
            "train_partition_digest": dataset_metadata.get("train_partition_digest") if dataset_metadata else None,
            "val_partition_digest": dataset_metadata.get("val_partition_digest") if dataset_metadata else None,
        },
        "target_environment": {
            "execution_mode": preflight_metadata.get("execution_mode") if preflight_metadata else None,
            "hardware_profile": preflight_metadata.get("target_hardware_profile") if preflight_metadata else None,
            "peak_memory_mb": preflight_metadata.get("peak_memory_mb") if preflight_metadata else None,
            "download_size_mb": preflight_metadata.get("download_size_mb") if preflight_metadata else None,
        },
        "provenance": {
            "recommendation_run_id": recommendation_metadata.get("run_id") if recommendation_metadata else None,
            "recommendation_candidate_id": recommendation_metadata.get("candidate_id") if recommendation_metadata else None,
            "configuration_digest": recommendation_metadata.get("configuration_digest") if recommendation_metadata else None,
        },
    }

    canonical_str = canonical_json_dumps(manifest)
    manifest_digest = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    return manifest, manifest_digest
