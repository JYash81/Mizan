"""SQLAlchemy models for Mizan Milestone 8: Hardware Knowledge Base & Pricing Catalog."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class EvidenceType(str, enum.Enum):
    """Evidence and verification classification for hardware and estimation records."""

    MEASURED = "MEASURED"
    VENDOR_REFERENCE = "VENDOR_REFERENCE"
    ESTIMATED = "ESTIMATED"
    SIMULATED = "SIMULATED"
    USER_SUPPLIED = "USER_SUPPLIED"
    UNVERIFIED = "UNVERIFIED"


class HardwareProfileCategory(str, enum.Enum):
    """Category of hardware compute profile."""

    LOCAL_WORKSTATION = "LOCAL_WORKSTATION"
    CLOUD_CPU = "CLOUD_CPU"
    CLOUD_GPU = "CLOUD_GPU"
    CUSTOM = "CUSTOM"


class PricingProvenance(str, enum.Enum):
    """Source provenance and reliability tier for infrastructure pricing records."""

    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    USER_SUPPLIED = "USER_SUPPLIED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    SYNTHETIC_TEST_DATA = "SYNTHETIC_TEST_DATA"
    UNVERIFIED = "UNVERIFIED"


class FeasibilityStatus(str, enum.Enum):
    """Feasibility outcome for resource and hardware estimates."""

    FEASIBLE_ESTIMATE = "FEASIBLE_ESTIMATE"
    LIKELY_FEASIBLE = "LIKELY_FEASIBLE"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HardwareProfile(Base):
    """Registered hardware execution profile with resource specs and capability flags."""

    __tablename__ = "hardware_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[HardwareProfileCategory] = mapped_column(
        Enum(HardwareProfileCategory), nullable=False, index=True
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), default=EvidenceType.VENDOR_REFERENCE, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CPU specifications
    cpu_manufacturer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cpu_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    physical_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logical_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_frequency_mhz: Mapped[float | None] = mapped_column(Float, nullable=True)
    system_ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    available_ram_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # GPU specifications (nullable for CPU-only profiles)
    gpu_vendor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gpu_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gpu_vram_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_bandwidth_gbps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Capability metadata (JSON arrays / dictionaries)
    supported_numeric_precisions_json: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )
    supported_runtimes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_quantizations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Execution flags
    supports_cpu_inference: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_gpu_inference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_fine_tuning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Provenance, documentation & limitations
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reference_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional multi-tenant scope (None = platform global reference profile)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def supported_numeric_precisions(self) -> list[str]:
        try:
            return json.loads(self.supported_numeric_precisions_json)
        except Exception:
            return []

    @property
    def supported_runtimes(self) -> list[str]:
        try:
            return json.loads(self.supported_runtimes_json)
        except Exception:
            return []

    @property
    def supported_quantizations(self) -> list[str]:
        try:
            return json.loads(self.supported_quantizations_json)
        except Exception:
            return []


class LocalHardwareSnapshot(Base):
    """Inspection record capturing local machine hardware specs and detection limitations."""

    __tablename__ = "local_hardware_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    cpu_model: Mapped[str] = mapped_column(String(255), nullable=False)
    physical_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logical_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system_ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    available_ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)

    os_name: Mapped[str] = mapped_column(String(64), nullable=False)
    os_release: Mapped[str] = mapped_column(String(64), nullable=False)
    architecture: Mapped[str] = mapped_column(String(32), nullable=False)

    has_nvidia_gpu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gpu_info_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), default=EvidenceType.MEASURED, nullable=False
    )
    detection_limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class HardwareBenchmark(Base):
    """Opt-in bounded CPU execution benchmark on local machine."""

    __tablename__ = "hardware_benchmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("local_hardware_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    benchmark_name: Mapped[str] = mapped_column(String(128), nullable=False)
    benchmark_version: Mapped[str] = mapped_column(String(32), nullable=False)
    workload_params_json: Mapped[str] = mapped_column(Text, nullable=False)

    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    operations_per_second: Mapped[float] = mapped_column(Float, nullable=False)
    ram_before_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    ram_after_mb: Mapped[int] = mapped_column(Integer, nullable=False)

    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), default=EvidenceType.MEASURED, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    limitations: Mapped[str] = mapped_column(Text, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class QuantizationFormatRecord(Base):
    """Centralized metadata and conversion parameters for supported quantization formats."""

    __tablename__ = "quantization_formats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    format_key: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    format_family: Mapped[str] = mapped_column(String(32), nullable=False)
    nominal_bits: Mapped[float] = mapped_column(Float, nullable=False)
    effective_reference_bits: Mapped[float] = mapped_column(Float, nullable=False)
    runtime_requirements_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_hardware_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    calculation_assumptions: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class ResourceEstimateRecord(Base):
    """Persisted resource and memory feasibility calculation for a model workload."""

    __tablename__ = "resource_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_count_millions: Mapped[float] = mapped_column(Float, nullable=False)
    quantization_format: Mapped[str] = mapped_column(String(32), nullable=False)
    context_length: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    hardware_profile_key: Mapped[str] = mapped_column(String(64), nullable=False)

    # Detailed calculated memory requirements in Megabytes
    weight_memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    artifact_size_mb: Mapped[float] = mapped_column(Float, nullable=False)
    kv_cache_memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    runtime_overhead_mb: Mapped[float] = mapped_column(Float, nullable=False)
    peak_memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    available_memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    headroom_mb: Mapped[float] = mapped_column(Float, nullable=False)

    feasibility_status: Mapped[FeasibilityStatus] = mapped_column(
        Enum(FeasibilityStatus), nullable=False, index=True
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), default=EvidenceType.ESTIMATED, nullable=False
    )
    calculation_details_json: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions_and_warnings_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class PricingCatalogEntry(Base):
    """Infrastructure pricing record with provenance classification and decimal currency rate."""

    __tablename__ = "pricing_catalog_entries"
    __table_args__ = (
        UniqueConstraint(
            "provider_name",
            "resource_type",
            "instance_type",
            "region",
            "catalog_version",
            name="uq_pricing_entry_resource_region_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    instance_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")

    # Hourly rate stored as string to prevent binary float inaccuracies
    hourly_rate: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_monthly_rate_per_gb: Mapped[str | None] = mapped_column(String(32), nullable=True)
    billing_unit_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)

    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provenance: Mapped[PricingProvenance] = mapped_column(
        Enum(PricingProvenance), default=PricingProvenance.REFERENCE_ONLY, nullable=False, index=True
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(32), nullable=False, default="2026.1")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
