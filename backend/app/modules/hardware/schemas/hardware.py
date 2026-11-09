"""Pydantic schemas for Hardware Knowledge Base, Local Detection, and Benchmarks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.hardware import EvidenceType, FeasibilityStatus, HardwareProfileCategory


class HardwareProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_key: str
    name: str
    category: HardwareProfileCategory
    evidence_type: EvidenceType
    description: str | None = None
    cpu_manufacturer: str | None = None
    cpu_model: str | None = None
    physical_cores: int | None = None
    logical_cores: int | None = None
    cpu_frequency_mhz: float | None = None
    system_ram_mb: int
    available_ram_mb: int | None = None
    gpu_vendor: str | None = None
    gpu_model: str | None = None
    gpu_vram_mb: int | None = None
    memory_bandwidth_gbps: float | None = None
    supported_numeric_precisions: list[str] = Field(default_factory=list)
    supported_runtimes: list[str] = Field(default_factory=list)
    supported_quantizations: list[str] = Field(default_factory=list)
    supports_cpu_inference: bool
    supports_gpu_inference: bool
    supports_fine_tuning: bool
    source_url: str | None = None
    reference_date: str | None = None
    verification_date: datetime | None = None
    limitations: str | None = None
    is_reference: bool
    organization_id: str | None = None
    workspace_id: str | None = None
    created_at: datetime
    updated_at: datetime


class HardwareProfileCreate(BaseModel):
    profile_key: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    category: HardwareProfileCategory = Field(default=HardwareProfileCategory.CUSTOM)
    description: str | None = None
    cpu_manufacturer: str | None = None
    cpu_model: str | None = None
    physical_cores: int | None = Field(default=None, ge=1)
    logical_cores: int | None = Field(default=None, ge=1)
    cpu_frequency_mhz: float | None = None
    system_ram_mb: int = Field(ge=512)
    available_ram_mb: int | None = None
    gpu_vendor: str | None = None
    gpu_model: str | None = None
    gpu_vram_mb: int | None = Field(default=None, ge=0)
    memory_bandwidth_gbps: float | None = None
    supported_numeric_precisions: list[str] = Field(default_factory=lambda: ["FP32", "INT8"])
    supported_runtimes: list[str] = Field(default_factory=lambda: ["ollama", "onnx", "mock"])
    supported_quantizations: list[str] = Field(default_factory=lambda: ["Q4_K_M", "Q8_0"])
    supports_cpu_inference: bool = True
    supports_gpu_inference: bool = False
    supports_fine_tuning: bool = False
    limitations: str | None = None


class LocalHardwareSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    cpu_model: str
    physical_cores: int | None = None
    logical_cores: int | None = None
    system_ram_mb: int
    available_ram_mb: int
    os_name: str
    os_release: str
    architecture: str
    has_nvidia_gpu: bool
    gpu_info: dict[str, Any] | None = None
    evidence_type: EvidenceType
    detection_limitations: str | None = None
    created_at: datetime


class BenchmarkRunRequest(BaseModel):
    matrix_size: int = Field(
        default=300, ge=50, le=1000, description="Matrix dimension for bounded compute test"
    )
    iterations: int = Field(
        default=5, ge=1, le=20, description="Repetitions for measurement stability"
    )


class BenchmarkRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    snapshot_id: str | None = None
    benchmark_name: str
    benchmark_version: str
    duration_ms: float
    operations_per_second: float
    ram_before_mb: int
    ram_after_mb: int
    evidence_type: EvidenceType
    status: str
    limitations: str
    started_at: datetime
    completed_at: datetime
    created_at: datetime


class QuantizationFormatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    format_key: str
    format_family: str
    nominal_bits: float
    effective_reference_bits: float
    runtime_requirements: list[str] = Field(default_factory=list)
    supported_hardware: list[str] = Field(default_factory=list)
    calculation_assumptions: str
    limitations: str
    source_reference: str
    registry_version: str


class ResourceEstimateRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=255)
    parameter_count_millions: float = Field(
        ge=1.0, le=1000000.0, description="Model parameter count in millions"
    )
    quantization_format: str = Field(default="Q4_K_M")
    context_length: int = Field(default=2048, ge=128, le=128000)
    batch_size: int = Field(default=1, ge=1, le=128)
    execution_mode: str = Field(
        default="INFERENCE_CPU",
        description="INFERENCE_CPU, INFERENCE_GPU, FINE_TUNE_LORA, FINE_TUNE_FULL",
    )
    hardware_profile_key: str = Field(default="LOCAL_CPU_I5_8GB")
    # Architecture metadata (optional, model-specific KV cache precision)
    num_layers: int | None = Field(default=None, ge=1, le=200)
    num_kv_heads: int | None = Field(default=None, ge=1, le=200)
    head_dim: int | None = Field(default=None, ge=1, le=512)
    hidden_size: int | None = Field(default=None, ge=64, le=32768)


class ResourceEstimateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    model_name: str
    parameter_count_millions: float
    quantization_format: str
    context_length: int
    batch_size: int
    execution_mode: str
    hardware_profile_key: str
    hardware_profile_name: str
    # Component breakdown (MB)
    weight_memory_mb: float
    artifact_size_mb: float
    kv_cache_memory_mb: float
    runtime_overhead_mb: float
    peak_memory_mb: float
    # Hardware limits & Headroom
    available_memory_mb: float
    headroom_mb: float
    feasibility_status: FeasibilityStatus
    evidence_type: EvidenceType
    calculation_details: dict[str, Any] = Field(default_factory=dict)
    assumptions_and_warnings: list[str] = Field(default_factory=list)


class HardwareComparisonRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=255)
    parameter_count_millions: float = Field(ge=1.0, le=1000000.0)
    quantization_format: str = Field(default="Q4_K_M")
    context_length: int = Field(default=2048, ge=128, le=128000)
    batch_size: int = Field(default=1, ge=1, le=128)
    execution_mode: str = Field(default="INFERENCE_CPU")
    num_layers: int | None = None
    num_kv_heads: int | None = None
    head_dim: int | None = None


class HardwareComparisonItem(BaseModel):
    profile_key: str
    profile_name: str
    category: str
    evidence_type: EvidenceType
    required_ram_mb: float
    required_vram_mb: float
    available_ram_mb: float
    available_vram_mb: float
    headroom_mb: float
    feasibility_status: FeasibilityStatus
    runtime_supported: bool
    quantization_supported: bool
    limitations: str | None = None
    reason: str


class HardwareComparisonResponse(BaseModel):
    model_name: str
    parameter_count_millions: float
    quantization_format: str
    context_length: int
    batch_size: int
    execution_mode: str
    profiles: list[HardwareComparisonItem] = Field(default_factory=list)
