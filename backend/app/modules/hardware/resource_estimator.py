"""Deterministic resource, memory, and peak execution estimator for AI models."""

from __future__ import annotations

from typing import Any

from app.models.hardware import EvidenceType, FeasibilityStatus
from app.modules.hardware.quantization_registry import (
    calculate_weight_bytes,
    get_quantization_info,
    is_quantization_supported,
)


def estimate_kv_cache_mb(
    param_count: float,
    context_length: int,
    batch_size: int,
    num_layers: int | None = None,
    num_kv_heads: int | None = None,
    head_dim: int | None = None,
    hidden_size: int | None = None,
) -> tuple[float, str]:
    """Calculate KV cache memory in Megabytes.

    Returns:
        (kv_cache_mb, calculation_method)
    """
    bytes_per_elem = 2.0  # FP16 KV cache

    # Exact architectural formula when layers, kv heads, and head dimension are provided
    if num_layers is not None and num_kv_heads is not None and head_dim is not None:
        # KV cache = 2 (key + value) * layers * kv_heads * head_dim * bytes_per_element * seq_len * batch
        total_bytes = (
            2.0
            * num_layers
            * num_kv_heads
            * head_dim
            * bytes_per_elem
            * context_length
            * batch_size
        )
        return round(total_bytes / (1024.0 * 1024.0), 2), "ARCHITECTURAL_METADATA"

    # Secondary formula when hidden size and layers are known (MHA approximation)
    if num_layers is not None and hidden_size is not None:
        total_bytes = 2.0 * num_layers * hidden_size * bytes_per_elem * context_length * batch_size
        return round(total_bytes / (1024.0 * 1024.0), 2), "HIDDEN_SIZE_APPROXIMATION"

    # Heuristic fallback based on parameter tier:
    # Standard transformer rule of thumb: ~0.15 MB per 1024 tokens per 1B parameters for GQA (or ~0.30 MB for MHA)
    params_in_billions = max(0.1, param_count / 1_000_000_000.0)
    heuristic_mb = params_in_billions * 0.20 * (context_length / 1024.0) * batch_size
    return round(max(2.0, heuristic_mb), 2), "HEURISTIC_FALLBACK"


def estimate_model_resources(
    model_name: str,
    parameter_count_millions: float,
    quantization_format: str,
    context_length: int = 2048,
    batch_size: int = 1,
    execution_mode: str = "INFERENCE_CPU",
    hardware_profile: dict[str, Any] | None = None,
    num_layers: int | None = None,
    num_kv_heads: int | None = None,
    head_dim: int | None = None,
    hidden_size: int | None = None,
) -> dict[str, Any]:
    """Calculate full memory breakdown, peak execution requirements, and hardware feasibility."""
    format_key = quantization_format.upper().strip()
    if not is_quantization_supported(format_key):
        raise ValueError(f"Unsupported quantization format: '{quantization_format}'.")

    param_count = parameter_count_millions * 1_000_000.0
    quant_info = get_quantization_info(format_key)

    assumptions_and_warnings: list[str] = []
    exec_mode = execution_mode.upper().strip()

    # 1. Weight Memory and Artifact Size
    weight_bytes = calculate_weight_bytes(param_count, format_key)
    weight_memory_mb = round(weight_bytes / (1024.0 * 1024.0), 2)
    # Artifact size includes container metadata and tensor tables (~2% overhead)
    artifact_size_mb = round(weight_memory_mb * 1.02, 2)

    # 2. KV Cache Memory
    kv_cache_mb, kv_method = estimate_kv_cache_mb(
        param_count=param_count,
        context_length=context_length,
        batch_size=batch_size,
        num_layers=num_layers,
        num_kv_heads=num_kv_heads,
        head_dim=head_dim,
        hidden_size=hidden_size,
    )
    if kv_method == "HEURISTIC_FALLBACK":
        assumptions_and_warnings.append(
            "KV cache calculated using heuristic parameter-tier fallback due to missing layer/head metadata."
        )

    # 3. Execution Overhead depending on Workload Mode
    if exec_mode == "INFERENCE_CPU":
        # Activation scratch space + runtime allocator buffer
        activation_mb = round(
            max(64.0, (batch_size * context_length * 4096 * 2.0) / (1024.0 * 1024.0) * 0.1),
            2,
        )
        runtime_overhead_mb = round(max(256.0, weight_memory_mb * 0.08) + activation_mb, 2)
        peak_memory_mb = round(weight_memory_mb + kv_cache_mb + runtime_overhead_mb, 2)

    elif exec_mode == "INFERENCE_GPU":
        # GPU context, CUDA runtime context (~500 MB), activations
        cuda_context_mb = 512.0
        activation_mb = round(
            max(128.0, (batch_size * context_length * 4096 * 2.0) / (1024.0 * 1024.0) * 0.15),
            2,
        )
        runtime_overhead_mb = round(cuda_context_mb + activation_mb, 2)
        peak_memory_mb = round(weight_memory_mb + kv_cache_mb + runtime_overhead_mb, 2)

    elif exec_mode == "FINE_TUNE_LORA":
        # Base model weights + LoRA adapters (1% params) + Adam optimizer for adapters (8 bytes/param) + gradients (4 bytes/param) + activation checkpointing
        lora_params = param_count * 0.01
        lora_weights_mb = (lora_params * 2.0) / (1024.0 * 1024.0)
        optimizer_mb = (lora_params * 8.0) / (1024.0 * 1024.0)
        gradients_mb = (lora_params * 4.0) / (1024.0 * 1024.0)
        activations_mb = max(512.0, weight_memory_mb * 0.25)
        runtime_overhead_mb = round(
            lora_weights_mb + optimizer_mb + gradients_mb + activations_mb + 512.0, 2
        )
        peak_memory_mb = round(weight_memory_mb + kv_cache_mb + runtime_overhead_mb, 2)
        assumptions_and_warnings.append(
            "LoRA fine-tuning assumes 1% trainable adapter parameter ratio and AdamW optimizer."
        )

    elif exec_mode == "FINE_TUNE_FULL":
        # Full parameter training: FP16/BF16 weights + FP32 Adam optimizer (16 bytes/param) + FP32 gradients (4 bytes/param) + full activations
        fp32_optimizer_mb = (param_count * 16.0) / (1024.0 * 1024.0)
        fp32_gradients_mb = (param_count * 4.0) / (1024.0 * 1024.0)
        training_activations_mb = max(1024.0, weight_memory_mb * 0.8)
        runtime_overhead_mb = round(
            fp32_optimizer_mb + fp32_gradients_mb + training_activations_mb, 2
        )
        peak_memory_mb = round(weight_memory_mb + kv_cache_mb + runtime_overhead_mb, 2)
        assumptions_and_warnings.append(
            "Full parameter fine-tuning requires optimizer states (16 bytes/param) and gradients (4 bytes/param)."
        )
    else:
        raise ValueError(f"Unsupported execution mode: '{execution_mode}'.")

    # Safety margin: 15% headroom buffer
    safety_margin_factor = 1.15
    required_with_margin_mb = round(peak_memory_mb * safety_margin_factor, 2)

    # 4. Feasibility Evaluation against Target Hardware
    hw = hardware_profile or {}
    hw_key = hw.get("profile_key", "GENERIC_ESTIMATE")
    hw_name = hw.get("name", "Generic Hardware Reference")

    # Determine available capacity based on CPU vs GPU execution
    if exec_mode == "INFERENCE_CPU":
        # On local CPU, reserve ~3 GB for Windows/OS and background apps
        total_ram = hw.get("system_ram_mb", 8192)
        available_memory_mb = hw.get("available_ram_mb") or max(1024, total_ram - 3072)
    else:
        # GPU workloads require VRAM
        available_memory_mb = hw.get("gpu_vram_mb", 0)

    headroom_mb = round(available_memory_mb - required_with_margin_mb, 2)

    # Evaluate compatibility rules
    feasibility_status = FeasibilityStatus.FEASIBLE_ESTIMATE

    # Rule A: AWQ format requires GPU
    if format_key == "AWQ" and exec_mode == "INFERENCE_CPU":
        feasibility_status = FeasibilityStatus.NOT_FEASIBLE
        assumptions_and_warnings.append(
            "AWQ quantization is strictly GPU-only. It cannot be executed on CPU runtimes."
        )

    # Rule B: GPU execution mode requested on CPU-only profile
    elif (
        exec_mode in ("INFERENCE_GPU", "FINE_TUNE_LORA", "FINE_TUNE_FULL")
        and available_memory_mb <= 0
    ):
        feasibility_status = FeasibilityStatus.NOT_FEASIBLE
        assumptions_and_warnings.append(
            f"Workload mode '{exec_mode}' requires a dedicated GPU, but hardware profile '{hw_key}' has no VRAM."
        )

    # Rule C: Insufficient memory headroom
    elif headroom_mb < -512.0:
        feasibility_status = FeasibilityStatus.NOT_FEASIBLE
        assumptions_and_warnings.append(
            f"Insufficient memory: required {required_with_margin_mb} MB exceeds available {available_memory_mb} MB by {abs(headroom_mb)} MB."
        )
    elif headroom_mb < 0.0:
        feasibility_status = FeasibilityStatus.LIKELY_FEASIBLE
        assumptions_and_warnings.append(
            f"Tight headroom: workload requires {required_with_margin_mb} MB (with 15% safety margin); fits raw peak {peak_memory_mb} MB with minimal margin."
        )

    return {
        "model_name": model_name,
        "parameter_count_millions": parameter_count_millions,
        "quantization_format": format_key,
        "context_length": context_length,
        "batch_size": batch_size,
        "execution_mode": exec_mode,
        "hardware_profile_key": hw_key,
        "hardware_profile_name": hw_name,
        "weight_memory_mb": weight_memory_mb,
        "artifact_size_mb": artifact_size_mb,
        "kv_cache_memory_mb": kv_cache_mb,
        "runtime_overhead_mb": runtime_overhead_mb,
        "peak_memory_mb": peak_memory_mb,
        "available_memory_mb": float(available_memory_mb),
        "headroom_mb": headroom_mb,
        "feasibility_status": feasibility_status,
        "evidence_type": EvidenceType.ESTIMATED,
        "calculation_details": {
            "effective_bits_per_weight": quant_info["effective_reference_bits"],
            "safety_margin_factor": safety_margin_factor,
            "required_with_safety_margin_mb": required_with_margin_mb,
            "kv_cache_calculation_method": kv_method,
            "nominal_format_family": quant_info["format_family"],
        },
        "assumptions_and_warnings": assumptions_and_warnings,
    }


class ResourceEstimatorService:
    """Service wrapper for calculating model resource requirements."""

    def __init__(self, profile_repo=None, quant_registry=None) -> None:
        self.profile_repo = profile_repo
        self.quant_registry = quant_registry

    def calculate_estimate(self, db: Any, payload: Any, workspace_id: str | None = None) -> Any:
        from app.modules.hardware.schemas.hardware import ResourceEstimateResponse

        hw_dict = None
        if payload.hardware_profile_key and self.profile_repo:
            prof = self.profile_repo.get_by_key(db, payload.hardware_profile_key, workspace_id)
            if prof:
                hw_dict = {
                    "profile_key": prof.profile_key,
                    "name": prof.name,
                    "system_ram_mb": prof.system_ram_mb,
                    "available_ram_mb": prof.available_ram_mb,
                    "gpu_vram_mb": prof.gpu_vram_mb,
                }
        est_dict = estimate_model_resources(
            model_name=payload.model_name,
            parameter_count_millions=payload.parameter_count_millions,
            quantization_format=payload.quantization_format,
            context_length=payload.context_length,
            batch_size=payload.batch_size,
            execution_mode=payload.execution_mode,
            hardware_profile=hw_dict,
            num_layers=payload.num_layers,
            num_kv_heads=payload.num_kv_heads,
            head_dim=payload.head_dim,
            hidden_size=payload.hidden_size,
        )
        return ResourceEstimateResponse(**est_dict)
