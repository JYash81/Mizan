"""Hardware preflight and memory estimation using Milestone 8 resource models."""

from __future__ import annotations

import json
from typing import Any

from app.models.hardware import EvidenceType, FeasibilityStatus
from app.models.model_building import ExecutionMode, ModelBuildRecipe, ModelSource, RecipeType
from app.modules.hardware.resource_estimator import estimate_model_resources

REFERENCE_PROFILES: dict[str, dict[str, Any]] = {
    "LOCAL_CPU_I5_8GB": {
        "profile_key": "LOCAL_CPU_I5_8GB",
        "name": "Local Workstation (Intel Core i5, 8 GB RAM)",
        "ram_mb": 8192,
        "available_ram_mb": 5120,
        "vram_mb": 0,
        "gpu_count": 0,
        "storage_gb": 50,
    },
    "NVIDIA_T4_16GB": {
        "profile_key": "NVIDIA_T4_16GB",
        "name": "NVIDIA Tesla T4 (16 GB GDDR6)",
        "ram_mb": 12800,
        "available_ram_mb": 11000,
        "vram_mb": 15360,
        "gpu_count": 1,
        "storage_gb": 100,
    },
    "REFERENCE_CPU_2VCPU_4GB": {
        "profile_key": "REFERENCE_CPU_2VCPU_4GB",
        "name": "Cloud Small CPU (2 vCPU, 4 GB RAM)",
        "ram_mb": 4096,
        "available_ram_mb": 3072,
        "vram_mb": 0,
        "gpu_count": 0,
        "storage_gb": 30,
    },
}

PROFILE_ALIASES: dict[str, str] = {
    "local_workstation_8gb": "LOCAL_CPU_I5_8GB",
    "cloud_t4_16gb": "NVIDIA_T4_16GB",
    "nvidia_t4": "NVIDIA_T4_16GB",
    "colab_free_t4": "NVIDIA_T4_16GB",
}


def run_build_preflight(
    model: ModelSource,
    recipe: ModelBuildRecipe,
    execution_mode: ExecutionMode,
    target_hardware_profile_key: str | None = None,
    batch_size: int = 1,
    context_length: int | None = None,
) -> dict[str, Any]:
    """Execute resource preflight check using M8 resource models.

    Computes:
    - Base model download footprint
    - Working memory (RAM, VRAM, optimizer, activations)
    - Disk storage requirements
    - Hardware profile feasibility
    """
    ctx_len = context_length or min(model.context_length, 2048)
    param_millions = model.parameter_count_millions

    # Map recipe type to M8 execution mode
    if recipe.recipe_type in (RecipeType.LORA_FINETUNE, RecipeType.QLORA_FINETUNE, RecipeType.SMOKE_TEST):
        m8_exec_mode = "FINE_TUNE_LORA"
    else:
        m8_exec_mode = "INFERENCE_CPU" if execution_mode == ExecutionMode.LOCAL_SMOKE_TEST else "INFERENCE_GPU"

    # Determine default hardware profile
    raw_key = target_hardware_profile_key
    if not raw_key:
        if execution_mode == ExecutionMode.LOCAL_SMOKE_TEST:
            raw_key = "LOCAL_CPU_I5_8GB"
        else:
            raw_key = "NVIDIA_T4_16GB"

    normalized_key = PROFILE_ALIASES.get(raw_key.lower().strip(), raw_key)
    profile = REFERENCE_PROFILES.get(normalized_key) or REFERENCE_PROFILES.get(normalized_key.upper()) or {
        "profile_key": normalized_key,
        "name": f"Hardware Profile ({normalized_key})",
        "ram_mb": 8192,
        "vram_mb": 0,
        "gpu_count": 0,
        "storage_gb": 50,
    }

    # Extract model layer/head metadata if available
    metadata = model.source_metadata
    num_layers = metadata.get("num_layers")
    num_kv_heads = metadata.get("num_kv_heads")
    head_dim = metadata.get("head_dim")
    hidden_size = metadata.get("hidden_size")

    # M8 Resource Estimation (FP16 baseline for weights)
    quant_format = "FP16"
    if recipe.recipe_type == RecipeType.QLORA_FINETUNE:
        quant_format = "Q4_K_M"  # 4-bit representation for base weights

    est = estimate_model_resources(
        model_name=model.name,
        parameter_count_millions=param_millions,
        quantization_format=quant_format,
        context_length=ctx_len,
        batch_size=batch_size,
        execution_mode=m8_exec_mode,
        hardware_profile=profile,
        num_layers=num_layers,
        num_kv_heads=num_kv_heads,
        head_dim=head_dim,
        hidden_size=hidden_size,
    )

    weight_mb = est.get("weight_memory_mb", 0.0)
    kv_cache_mb = est.get("kv_cache_memory_mb", 0.0)
    peak_memory_mb = est.get("peak_memory_mb", 0.0)

    # Calculate Disk Requirements
    download_size_mb = round(model.estimated_download_bytes / (1024.0 * 1024.0), 2)
    # Temporary conversion disk + checkpoint buffer (2x weight size) + output artifacts
    checkpoint_buffer_mb = round(weight_mb * 0.25 * 3, 2)  # 3 checkpoints of adapter
    output_artifact_mb = round(weight_mb * 0.1, 2)  # LoRA adapter is ~1-10% of base model
    total_disk_required_mb = round(
        download_size_mb + weight_mb + checkpoint_buffer_mb + output_artifact_mb + 2048.0, 2
    )

    # Feasibility Evaluation against Target Profile
    is_feasible = True
    block_reasons: list[str] = []

    profile_ram = profile.get("ram_mb", 8192)
    profile_vram = profile.get("vram_mb", 0)
    has_gpu = profile_vram > 0 or profile.get("gpu_count", 0) > 0

    recipe_reqs = {}
    if recipe.resource_requirements_json:
        try:
            recipe_reqs = json.loads(recipe.resource_requirements_json)
        except Exception:
            recipe_reqs = {}

    requires_gpu = recipe_reqs.get("requires_gpu", False)
    max_params = recipe_reqs.get("max_parameter_count_millions", 10000.0)

    if param_millions > max_params:
        is_feasible = False
        block_reasons.append(
            f"Model parameter count ({param_millions:.0f}M) exceeds recipe maximum of {max_params:.0f}M."
        )

    # Local host restrictions (CPU-only, 8 GB RAM)
    if execution_mode == ExecutionMode.LOCAL_SMOKE_TEST:
        if requires_gpu:
            is_feasible = False
            block_reasons.append("Recipe requires GPU acceleration, but local machine is CPU-only.")
        # Local RAM safety limit: leave 4 GB for OS and applications
        if peak_memory_mb > 4096.0:
            is_feasible = False
            block_reasons.append(
                f"Peak memory {peak_memory_mb:.1f} MB exceeds safe local execution threshold (4096 MB) on 8 GB RAM host."
            )
    else:
        # Colab Free / Cloud Profile
        if peak_memory_mb > profile_ram:
            is_feasible = False
            block_reasons.append(
                f"Peak memory {peak_memory_mb:.1f} MB exceeds target system RAM ({profile_ram} MB)."
            )
        if requires_gpu and not has_gpu:
            is_feasible = False
            block_reasons.append(f"Target profile '{profile.get('name')}' does not have dedicated GPU VRAM.")
        if profile_vram > 0 and peak_memory_mb > profile_vram:
            is_feasible = False
            block_reasons.append(
                f"Peak memory {peak_memory_mb:.1f} MB exceeds target GPU VRAM ({profile_vram} MB)."
            )

    feasibility_status = FeasibilityStatus.FEASIBLE_ESTIMATE if is_feasible else FeasibilityStatus.NOT_FEASIBLE

    return {
        "model_key": model.model_key,
        "recipe_key": recipe.recipe_key,
        "execution_mode": execution_mode.value,
        "target_hardware_profile": profile.get("profile_key", "custom"),
        "hardware_name": profile.get("name", "Unknown Hardware"),
        "weight_memory_mb": weight_mb,
        "kv_cache_mb": kv_cache_mb,
        "peak_memory_mb": peak_memory_mb,
        "download_size_mb": download_size_mb,
        "total_disk_required_mb": total_disk_required_mb,
        "feasibility_status": feasibility_status.value,
        "is_feasible": is_feasible,
        "block_reasons": block_reasons,
        "evidence_type": EvidenceType.ESTIMATED.value,
    }
