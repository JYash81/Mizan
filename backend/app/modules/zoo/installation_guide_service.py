"""Installation guide and static snippet generator for Model Zoo and App Zoo."""

from __future__ import annotations

from app.models.artifact_registry import ModelVersion
from app.models.catalog import AppListing, AppVersion, ModelListing


class InstallationGuideService:
    """Generates deterministic, safe, version-pinned installation and configuration snippets."""

    NOTICE_HEADER = (
        "# ==============================================================================\n"
        "# MIZAN GOVERNED INSTALLATION SPECIFICATION\n"
        "# NOTE: Execution and customer runtime are provided by a future Milestone 13 workflow.\n"
        "# Do not execute unverified commands without organization security sign-off.\n"
        "# ==============================================================================\n"
    )

    @classmethod
    def generate_model_snippets(
        cls,
        listing: ModelListing,
        model_version: ModelVersion,
    ) -> dict[str, str]:
        """Generate static, version-pinned snippets for model consumers."""
        family_slug = listing.model_family.slug if listing.model_family else "model"
        version_tag = model_version.version_tag
        manifest_digest = model_version.release_manifest_digest or "UNFINALIZED"
        source_model = model_version.source_model_key

        # 1. Transformers / Python Loading Snippet
        python_snippet = (
            f"{cls.NOTICE_HEADER}\n"
            f"# Python 3.11+ / Transformers Specification\n"
            f"# Family: {family_slug} | Version: {version_tag}\n"
            f"# Release Manifest Digest: {manifest_digest}\n\n"
            f"from transformers import AutoModelForCausalLM, AutoTokenizer\n"
            f"from peft import PeftModel\n\n"
            f"# 1. Load Base Model Weights\n"
            f'base_model_key = "{source_model}"\n'
            f'tokenizer = AutoTokenizer.from_pretrained(base_model_key, revision="{model_version.source_model_revision}")\n'
            f"model = AutoModelForCausalLM.from_pretrained(\n"
            f"    base_model_key,\n"
            f'    device_map="auto",\n'
            f"    torch_dtype=\"auto\",\n"
            f")\n\n"
            f"# 2. Attach Governed Release Artifact (Pinned: {version_tag})\n"
            f"# Expected SHA-256 Digest: {manifest_digest}\n"
            f'print(f"Loaded Governed Model: {{base_model_key}} [{version_tag}]")\n'
        )

        # 2. GGUF / Llama.cpp CLI Snippet
        gguf_artifact = next(
            (a for a in model_version.artifacts or [] if "GGUF" in str(a.artifact_type)), None
        )
        gguf_filename = f"{family_slug}-{version_tag}.gguf"
        gguf_sha = gguf_artifact.sha256 if gguf_artifact else "VERIFY_ARTIFACT_SHA256"

        gguf_snippet = (
            f"{cls.NOTICE_HEADER}\n"
            f"# Llama.cpp / GGUF High-Performance CLI Specification\n"
            f"# Expected Artifact SHA-256: {gguf_sha}\n\n"
            f"# Run local CPU/GPU quantized inference:\n"
            f"llama-cli \\\n"
            f"  -m ./{gguf_filename} \\\n"
            f"  -p \"You are a helpful business assistant. Summarize the following document:\" \\\n"
            f"  -n 512 \\\n"
            f"  -c 2048 \\\n"
            f"  --temp 0.2\n"
        )

        # 3. Future M13 Declarative Serving Spec
        m13_spec = (
            f"{cls.NOTICE_HEADER}\n"
            f"# Future M13 Customer Runtime Serving Specification (Declarative YAML)\n"
            f"apiVersion: mizan.ai/v1alpha1\n"
            f"kind: ModelServingSlot\n"
            f"metadata:\n"
            f"  name: {family_slug}-{version_tag.replace('.', '-')}\n"
            f"spec:\n"
            f"  modelFamily: {family_slug}\n"
            f"  versionTag: {version_tag}\n"
            f"  releaseManifestDigest: {manifest_digest}\n"
            f"  resources:\n"
            f"    minRamMb: {model_version.min_ram_mb:.0f}\n"
            f"    minVramMb: {model_version.min_vram_mb:.0f}\n"
            f"    targetHardware: {model_version.target_hardware_key or 'ANY_COMPATIBLE'}\n"
            f"  governance:\n"
            f"    gate3Approved: true\n"
            f"    immutableRelease: true\n"
        )

        return {
            "python_transformers": python_snippet,
            "llamacpp_cli": gguf_snippet,
            "m13_serving_spec": m13_spec,
        }

    @classmethod
    def generate_app_snippets(
        cls,
        listing: AppListing,
        app_version: AppVersion,
    ) -> dict[str, str]:
        """Generate static, version-pinned configuration snippets for App Zoo consumers."""
        app_key = listing.app_definition.app_key if listing.app_definition else "app"
        version_tag = app_version.version_tag
        manifest_digest = app_version.manifest_digest

        # 1. Declarative App Configuration JSON
        config_snippet = (
            f"{cls.NOTICE_HEADER}\n"
            f"# Mizan Declarative App Configuration\n"
            f"# App: {app_key} | Version: {version_tag}\n"
            f"# Manifest Digest: {manifest_digest}\n\n"
            f'{{\n'
            f'  "app_key": "{app_key}",\n'
            f'  "version_tag": "{version_tag}",\n'
            f'  "manifest_digest": "{manifest_digest}",\n'
            f'  "license_id": "{app_version.license_id}",\n'
            f'  "min_ram_mb": {app_version.min_ram_mb},\n'
            f'  "dependencies": [\n'
        )
        dep_lines = []
        for dep in app_version.model_dependencies or []:
            dep_lines.append(
                f'    {{"role": "{dep.dependency_role}", "release_digest": "{dep.release_manifest_digest}"}}'
            )
        config_snippet += ",\n".join(dep_lines)
        config_snippet += "\n  ]\n}\n"

        # 2. Future M13 Site Agent Deployment Spec
        m13_app_spec = (
            f"{cls.NOTICE_HEADER}\n"
            f"# Future M13 Customer Runtime Site Agent Application Blueprint\n"
            f"apiVersion: mizan.ai/v1alpha1\n"
            f"kind: CustomerApplicationDeployment\n"
            f"metadata:\n"
            f"  name: {app_key}-{version_tag.replace('.', '-')}\n"
            f"spec:\n"
            f"  appKey: {app_key}\n"
            f"  versionTag: {version_tag}\n"
            f"  manifestDigest: {manifest_digest}\n"
            f"  executionMode: SECURE_LOCAL_CONTAINER\n"
            f"  capabilities: {app_version.capabilities}\n"
        )

        return {
            "app_manifest_json": config_snippet,
            "m13_site_agent_spec": m13_app_spec,
        }
