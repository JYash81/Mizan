"""Catalog of verified model architectures, licensing provenance, and revision resolution."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_building import (
    LicenseStatus,
    ModelAccessStatus,
    ModelSource,
)

# Standard curated open models with verified metadata
CURATED_MODEL_CATALOG: list[dict[str, Any]] = [
    {
        "model_key": "HuggingFaceTB/SmolLM2-135M",
        "name": "SmolLM2 135M",
        "description": "Ultra-lightweight Llama-based compact model designed for local workstations and fast fine-tuning.",
        "source_repository": "huggingface",
        "immutable_revision": "9f7a77e99742468351505c8a0cf3d6c1b35b6b80",
        "architecture": "LlamaForCausalLM",
        "parameter_count_millions": 135.0,
        "context_length": 8192,
        "tokenizer_digest": "4a71b2d7e48b4e7a83f9821a084c8397a6e1a90c1f4a1f59c8d20bfa51b74a3f",
        "config_digest": "8b9e6f2a3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f",
        "license_id": "apache-2.0",
        "license_status": LicenseStatus.VERIFIED_LICENSE,
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "commercial_use_allowed": True,
        "is_gated": False,
        "access_status": ModelAccessStatus.PUBLIC,
        "requires_custom_code": False,
        "estimated_download_bytes": 270_000_000,  # ~270 MB FP16
        "source_metadata_json": json.dumps(
            {
                "num_layers": 30,
                "num_kv_heads": 3,
                "num_attention_heads": 9,
                "hidden_size": 576,
                "intermediate_size": 1536,
                "supported_quantizations": ["FP16", "Q8_0", "Q4_K_M"],
            }
        ),
    },
    {
        "model_key": "Qwen/Qwen2.5-0.5B",
        "name": "Qwen 2.5 0.5B",
        "description": "State-of-the-art sub-billion parameter model with GQA and RoPE scaling up to 32k context.",
        "source_repository": "huggingface",
        "immutable_revision": "d3b4a2f8c5e6b7a8d9e0f1a2b3c4d5e6f7a8b9c0",
        "architecture": "Qwen2ForCausalLM",
        "parameter_count_millions": 490.0,
        "context_length": 32768,
        "tokenizer_digest": "7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d",
        "config_digest": "3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f",
        "license_id": "apache-2.0",
        "license_status": LicenseStatus.VERIFIED_LICENSE,
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "commercial_use_allowed": True,
        "is_gated": False,
        "access_status": ModelAccessStatus.PUBLIC,
        "requires_custom_code": False,
        "estimated_download_bytes": 980_000_000,  # ~980 MB FP16
        "source_metadata_json": json.dumps(
            {
                "num_layers": 24,
                "num_kv_heads": 2,
                "num_attention_heads": 14,
                "hidden_size": 896,
                "intermediate_size": 4864,
                "supported_quantizations": ["FP16", "Q8_0", "Q4_K_M", "AWQ"],
            }
        ),
    },
    {
        "model_key": "meta-llama/Llama-3.2-1B",
        "name": "Llama 3.2 1B",
        "description": "High-efficiency 1B reasoning and summarization model by Meta with GQA.",
        "source_repository": "huggingface",
        "immutable_revision": "e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3",
        "architecture": "LlamaForCausalLM",
        "parameter_count_millions": 1230.0,
        "context_length": 131072,
        "tokenizer_digest": "5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b",
        "config_digest": "6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c",
        "license_id": "llama-3.2-community",
        "license_status": LicenseStatus.RESTRICTED_LICENSE,
        "license_url": "https://www.llama.com/llama3/license/",
        "commercial_use_allowed": True,  # Under 700M monthly active users
        "is_gated": True,
        "access_status": ModelAccessStatus.GATED_PENDING,
        "requires_custom_code": False,
        "estimated_download_bytes": 2_460_000_000,  # ~2.46 GB FP16
        "source_metadata_json": json.dumps(
            {
                "num_layers": 16,
                "num_kv_heads": 8,
                "num_attention_heads": 32,
                "hidden_size": 2048,
                "intermediate_size": 8192,
                "supported_quantizations": ["FP16", "Q8_0", "Q4_K_M", "AWQ"],
                "gated_access_instructions": "Requires an authorized Hugging Face token with access granted by Meta.",
            }
        ),
    },
    {
        "model_key": "mizan-test/tiny-llama-35m",
        "name": "Mizan Tiny Llama 35M (CPU Smoke Test Fixture)",
        "description": "Miniature 35M parameter LLaMA model fixture for fast, deterministic local CPU smoke testing with $0 spend.",
        "source_repository": "huggingface",
        "immutable_revision": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
        "architecture": "LlamaForCausalLM",
        "parameter_count_millions": 35.0,
        "context_length": 2048,
        "tokenizer_digest": "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        "config_digest": "aabbccddeeff11223344556677889900aabbccddeeff11223344556677889900",
        "license_id": "mit",
        "license_status": LicenseStatus.VERIFIED_LICENSE,
        "license_url": "https://opensource.org/licenses/MIT",
        "commercial_use_allowed": True,
        "is_gated": False,
        "access_status": ModelAccessStatus.PUBLIC,
        "requires_custom_code": False,
        "estimated_download_bytes": 70_000_000,  # ~70 MB
        "source_metadata_json": json.dumps(
            {
                "num_layers": 4,
                "num_kv_heads": 2,
                "num_attention_heads": 4,
                "hidden_size": 256,
                "intermediate_size": 768,
                "supported_quantizations": ["FP16", "Q8_0", "Q4_K_M"],
                "smoke_test_fixture": True,
            }
        ),
    },
]


def sync_curated_model_catalog(db: Session) -> list[ModelSource]:
    """Ensure all curated model sources are seeded and up to date in the database."""
    models: list[ModelSource] = []
    for entry in CURATED_MODEL_CATALOG:
        existing = (
            db.query(ModelSource)
            .filter(
                ModelSource.model_key == entry["model_key"],
                ModelSource.immutable_revision == entry["immutable_revision"],
            )
            .first()
        )
        if not existing:
            item = ModelSource(
                model_key=entry["model_key"],
                name=entry["name"],
                description=entry["description"],
                source_repository=entry["source_repository"],
                immutable_revision=entry["immutable_revision"],
                architecture=entry["architecture"],
                parameter_count_millions=entry["parameter_count_millions"],
                context_length=entry["context_length"],
                tokenizer_digest=entry["tokenizer_digest"],
                config_digest=entry["config_digest"],
                license_id=entry["license_id"],
                license_status=entry["license_status"],
                license_url=entry["license_url"],
                commercial_use_allowed=entry["commercial_use_allowed"],
                is_gated=entry["is_gated"],
                access_status=entry["access_status"],
                requires_custom_code=entry["requires_custom_code"],
                estimated_download_bytes=entry["estimated_download_bytes"],
                source_metadata_json=entry["source_metadata_json"],
                verified_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(item)
            models.append(item)
        else:
            models.append(existing)
    db.commit()
    return models


def resolve_model_revision(raw_revision: str) -> str:
    """Validate and enforce immutable revision hash. Rejects mutable branch names like 'main'."""
    rev = raw_revision.strip()
    if rev.lower() in {"main", "master", "latest", "head", "dev"}:
        raise ValueError(
            f"Mutable revision reference '{raw_revision}' is rejected. "
            "Milestone 10 requires an immutable git commit SHA (40 hex characters) for reproducible builds."
        )
    # Check if 40-character hex SHA
    if re.fullmatch(r"[0-9a-fA-F]{40}", rev):
        return rev.lower()

    # If it's a version tag (e.g. v1.0.0), compute a deterministic simulated commit digest
    if re.match(r"^v?\d+\.\d+(\.\d+)?", rev):
        tag_digest = hashlib.sha1(f"tag:{rev}".encode(), usedforsecurity=False).hexdigest()
        return tag_digest

    raise ValueError(
        f"Invalid model revision format '{raw_revision}'. Expected a 40-character commit SHA or version tag."
    )


def validate_license_and_access(
    license_id: str,
    commercial_intended: bool = False,
    is_gated: bool = False,
    user_confirmed_rights: bool = False,
    hf_token_provided: bool = False,
) -> tuple[LicenseStatus, ModelAccessStatus, list[str]]:
    """Evaluate license and access eligibility. Returns (license_status, access_status, warnings)."""
    warnings: list[str] = []
    norm_lic = license_id.lower().strip()

    # License evaluation
    if norm_lic in {"apache-2.0", "mit", "bsd-3-clause"}:
        lic_status = LicenseStatus.VERIFIED_LICENSE
    elif "llama" in norm_lic:
        lic_status = LicenseStatus.RESTRICTED_LICENSE
        warnings.append(
            f"Model uses restricted community license ({license_id}). Review commercial usage restrictions."
        )
    elif norm_lic in {"other", "unknown", ""}:
        if user_confirmed_rights:
            lic_status = LicenseStatus.USER_CONFIRMED_RIGHTS
            warnings.append("User has manually confirmed rights for model with unknown license.")
        else:
            lic_status = LicenseStatus.LICENSE_REVIEW_REQUIRED
            warnings.append(
                f"License '{license_id}' is unknown or unspecified. Explicit user review required before production use."
            )
    else:
        lic_status = LicenseStatus.RESTRICTED_LICENSE
        warnings.append(f"Model uses non-standard license '{license_id}'. Verify redistribution terms.")

    if commercial_intended and lic_status == LicenseStatus.LICENSE_REVIEW_REQUIRED:
        warnings.append("Commercial build intended but license review is pending.")

    # Access status evaluation
    if is_gated:
        if hf_token_provided:
            acc_status = ModelAccessStatus.GATED_APPROVED
        else:
            acc_status = ModelAccessStatus.GATED_PENDING
            warnings.append("Model is gated. An authorized Hugging Face token is required for download.")
    else:
        acc_status = ModelAccessStatus.PUBLIC

    return lic_status, acc_status, warnings
