"""Public metadata sanitization engine for Mizan Model Zoo and App Zoo."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.artifact_registry import ModelVersion
from app.models.catalog import AppListing, AppVersion, ModelListing


class PublicMetadataSanitizer:
    """Sanitizes catalog listings by stripping tenant-private data, raw file paths, and internal identifiers."""

    @staticmethod
    def sanitize_model_listing(
        listing: ModelListing,
        model_version: ModelVersion,
        hardware_badges: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Produce a sanitized public dictionary and deterministic SHA-256 publication digest for a ModelListing."""
        sanitized_artifacts: list[dict[str, Any]] = []
        for art in model_version.artifacts or []:
            sanitized_artifacts.append(
                {
                    "artifact_type": art.artifact_type.value if hasattr(art.artifact_type, "value") else str(art.artifact_type),
                    "format": art.format,
                    "quantization_type": art.quantization_type,
                    "file_size_bytes": art.file_size_bytes,
                    "sha256": art.sha256,
                    "is_primary_weights": art.is_primary_weights,
                }
            )
        # Sort artifacts deterministically by SHA-256
        sanitized_artifacts.sort(key=lambda a: a["sha256"])

        # Provenance summary (public evaluation & license metadata only)
        prov_summary = model_version.provenance_summary
        checks = prov_summary.get("checks", {})
        license_check = checks.get("BASE_MODEL_LICENSE", {}).get("details", {})

        payload: dict[str, Any] = {
            "title": listing.title,
            "slug": listing.slug,
            "description": listing.description,
            "detailed_description": listing.detailed_description or "",
            "category": listing.category,
            "tags": listing.tags,
            "distribution_status": listing.distribution_status.value if hasattr(listing.distribution_status, "value") else str(listing.distribution_status),
            "model_family": {
                "name": listing.model_family.name if listing.model_family else "",
                "slug": listing.model_family.slug if listing.model_family else "",
                "task_type": listing.model_family.task_type if listing.model_family else "TEXT_GENERATION",
            },
            "model_version": {
                "version_tag": model_version.version_tag,
                "source_model_key": model_version.source_model_key,
                "source_model_revision": model_version.source_model_revision,
                "recipe_key": model_version.recipe_key,
                "release_manifest_digest": model_version.release_manifest_digest or "",
            },
            "evaluation": {
                "base_score": model_version.base_evaluation_score,
                "final_score": model_version.final_evaluation_score,
                "quality_delta": model_version.quality_delta,
            },
            "hardware_requirements": {
                "min_ram_mb": model_version.min_ram_mb,
                "min_vram_mb": model_version.min_vram_mb,
                "target_hardware_key": model_version.target_hardware_key,
            },
            "hardware_badges": hardware_badges or [],
            "artifacts": sanitized_artifacts,
            "license": {
                "license_id": license_check.get("license", "Open-Weights"),
                "commercial_use_allowed": license_check.get("commercial_use", True),
                "is_gated": license_check.get("is_gated", False),
            },
        }

        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return payload, digest

    @staticmethod
    def sanitize_app_listing(
        listing: AppListing,
        app_version: AppVersion,
        hardware_badges: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Produce a sanitized public dictionary and deterministic SHA-256 publication digest for an AppListing."""
        deps: list[dict[str, Any]] = []
        for dep in app_version.model_dependencies or []:
            deps.append(
                {
                    "model_family_slug": dep.model_version.family.slug if dep.model_version and dep.model_version.family else "",
                    "model_version_tag": dep.model_version.version_tag if dep.model_version else "",
                    "release_manifest_digest": dep.release_manifest_digest,
                    "dependency_role": dep.dependency_role,
                }
            )
        deps.sort(key=lambda d: d["release_manifest_digest"])

        payload: dict[str, Any] = {
            "title": listing.title,
            "slug": listing.slug,
            "description": listing.description,
            "detailed_description": listing.detailed_description or "",
            "category": listing.category,
            "tags": listing.tags,
            "distribution_status": listing.distribution_status.value if hasattr(listing.distribution_status, "value") else str(listing.distribution_status),
            "app_definition": {
                "app_key": listing.app_definition.app_key if listing.app_definition else "",
                "name": listing.app_definition.name if listing.app_definition else "",
                "category": listing.app_definition.category if listing.app_definition else "",
            },
            "app_version": {
                "version_tag": app_version.version_tag,
                "manifest_digest": app_version.manifest_digest,
                "license_id": app_version.license_id,
                "capabilities": app_version.capabilities,
                "supported_input_types": app_version.supported_input_types,
                "supported_output_types": app_version.supported_output_types,
                "supported_languages": app_version.supported_languages,
            },
            "hardware_requirements": {
                "min_ram_mb": app_version.min_ram_mb,
                "min_vram_mb": app_version.min_vram_mb,
                "target_hardware_key": app_version.target_hardware_key,
            },
            "hardware_badges": hardware_badges or [],
            "model_dependencies": deps,
        }

        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return payload, digest
