"""Hardware compatibility evaluation service across reference profiles."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.hardware import FeasibilityStatus, HardwareProfile
from app.modules.hardware.resource_estimator import estimate_model_resources


def compare_workload_compatibility(
    db: Session,
    model_name: str,
    parameter_count_millions: float,
    quantization_format: str,
    context_length: int = 2048,
    batch_size: int = 1,
    execution_mode: str = "INFERENCE_CPU",
    num_layers: int | None = None,
    num_kv_heads: int | None = None,
    head_dim: int | None = None,
) -> list[dict[str, Any]]:
    """Compare a model workload across all registered reference hardware profiles."""
    profiles = (
        db.query(HardwareProfile)
        .filter(HardwareProfile.is_reference.is_(True))
        .order_by(HardwareProfile.category)
        .all()
    )

    results: list[dict[str, Any]] = []

    for prof in profiles:
        prof_dict = {
            "profile_key": prof.profile_key,
            "name": prof.name,
            "category": prof.category.value,
            "evidence_type": prof.evidence_type,
            "system_ram_mb": prof.system_ram_mb,
            "available_ram_mb": prof.available_ram_mb,
            "gpu_vram_mb": prof.gpu_vram_mb or 0,
            "supported_quantizations": prof.supported_quantizations,
            "supported_runtimes": prof.supported_runtimes,
            "supports_cpu_inference": prof.supports_cpu_inference,
            "supports_gpu_inference": prof.supports_gpu_inference,
            "supports_fine_tuning": prof.supports_fine_tuning,
            "limitations": prof.limitations,
        }

        # Adapt execution mode for target hardware: if hardware is CPU-only, check CPU feasibility; if GPU, check GPU mode
        effective_mode = execution_mode
        if prof.gpu_vram_mb and prof.gpu_vram_mb > 0 and execution_mode == "INFERENCE_CPU":
            # Can also run CPU offload or GPU inference
            effective_mode = "INFERENCE_GPU"

        est = estimate_model_resources(
            model_name=model_name,
            parameter_count_millions=parameter_count_millions,
            quantization_format=quantization_format,
            context_length=context_length,
            batch_size=batch_size,
            execution_mode=effective_mode,
            hardware_profile=prof_dict,
            num_layers=num_layers,
            num_kv_heads=num_kv_heads,
            head_dim=head_dim,
        )

        # Check quantization and runtime support
        quant_supported = quantization_format.upper() in prof.supported_quantizations
        runtime_supported = (
            prof.supports_gpu_inference
            if effective_mode in ("INFERENCE_GPU", "FINE_TUNE_LORA", "FINE_TUNE_FULL")
            else prof.supports_cpu_inference
        )

        status = est["feasibility_status"]
        if not quant_supported:
            status = FeasibilityStatus.NOT_FEASIBLE
            reason = f"Quantization '{quantization_format}' not supported on {prof.name}."
        elif not runtime_supported:
            status = FeasibilityStatus.NOT_FEASIBLE
            reason = (
                f"Workload mode '{effective_mode}' is not supported by {prof.name} architecture."
            )
        elif status == FeasibilityStatus.FEASIBLE_ESTIMATE:
            reason = f"Estimated to fit with {est['headroom_mb']} MB headroom."
        elif status == FeasibilityStatus.LIKELY_FEASIBLE:
            reason = f"Fits raw peak memory ({est['peak_memory_mb']} MB), but headroom is marginal ({est['headroom_mb']} MB)."
        else:
            reason = f"Memory exceeded: requires {est['calculation_details']['required_with_safety_margin_mb']} MB vs available {est['available_memory_mb']} MB."

        required_ram = est["peak_memory_mb"] if effective_mode == "INFERENCE_CPU" else 2048.0
        required_vram = (
            est["peak_memory_mb"]
            if effective_mode in ("INFERENCE_GPU", "FINE_TUNE_LORA", "FINE_TUNE_FULL")
            else 0.0
        )

        results.append(
            {
                "profile_key": prof.profile_key,
                "profile_name": prof.name,
                "category": prof.category.value,
                "evidence_type": prof.evidence_type,
                "required_ram_mb": required_ram,
                "required_vram_mb": required_vram,
                "available_ram_mb": float(prof.available_ram_mb or prof.system_ram_mb),
                "available_vram_mb": float(prof.gpu_vram_mb or 0),
                "headroom_mb": est["headroom_mb"],
                "feasibility_status": status,
                "runtime_supported": runtime_supported,
                "quantization_supported": quant_supported,
                "limitations": prof.limitations,
                "reason": reason,
            }
        )

    return results


class CompatibilityService:
    """Service wrapper for evaluating model compatibility across hardware profiles."""

    def __init__(self, estimator=None, profile_repo=None) -> None:
        self.estimator = estimator
        self.profile_repo = profile_repo

    def compare_all_profiles(
        self, db: Session, payload: Any, workspace_id: str | None = None
    ) -> Any:
        from app.modules.hardware.schemas.hardware import (
            HardwareComparisonItem,
            HardwareComparisonResponse,
        )

        raw_results = compare_workload_compatibility(
            db=db,
            model_name=payload.model_name,
            parameter_count_millions=payload.parameter_count_millions,
            quantization_format=payload.quantization_format,
            context_length=payload.context_length,
            batch_size=payload.batch_size,
            execution_mode=payload.execution_mode,
            num_layers=payload.num_layers,
            num_kv_heads=payload.num_kv_heads,
            head_dim=payload.head_dim,
        )
        items = [HardwareComparisonItem(**item) for item in raw_results]
        return HardwareComparisonResponse(
            model_name=payload.model_name,
            parameter_count_millions=payload.parameter_count_millions,
            quantization_format=payload.quantization_format,
            context_length=payload.context_length,
            batch_size=payload.batch_size,
            execution_mode=payload.execution_mode,
            profiles=items,
        )
