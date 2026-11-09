"""Add hardware profiles, benchmarks, estimates, pricing catalog, and Gate 2 approval models.

Revision ID: 20261108_0009
Revises: 20261108_0008
"""

import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "20261108_0009"
down_revision = "20261108_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. hardware_profiles
    op.create_table(
        "hardware_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile_key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="VENDOR_REFERENCE"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cpu_manufacturer", sa.String(64), nullable=True),
        sa.Column("cpu_model", sa.String(128), nullable=True),
        sa.Column("physical_cores", sa.Integer(), nullable=True),
        sa.Column("logical_cores", sa.Integer(), nullable=True),
        sa.Column("cpu_frequency_mhz", sa.Float(), nullable=True),
        sa.Column("system_ram_mb", sa.Integer(), nullable=False),
        sa.Column("available_ram_mb", sa.Integer(), nullable=True),
        sa.Column("gpu_vendor", sa.String(64), nullable=True),
        sa.Column("gpu_model", sa.String(128), nullable=True),
        sa.Column("gpu_vram_mb", sa.Integer(), nullable=True),
        sa.Column("memory_bandwidth_gbps", sa.Float(), nullable=True),
        sa.Column("supported_numeric_precisions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_runtimes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_quantizations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supports_cpu_inference", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_gpu_inference", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_fine_tuning", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("reference_date", sa.String(32), nullable=True),
        sa.Column("verification_date", sa.DateTime(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("is_reference", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hardware_profiles_key", "hardware_profiles", ["profile_key"])
    op.create_index("ix_hardware_profiles_category", "hardware_profiles", ["category"])
    op.create_index("ix_hardware_profiles_workspace", "hardware_profiles", ["workspace_id"])

    # 2. local_hardware_snapshots
    op.create_table(
        "local_hardware_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cpu_model", sa.String(255), nullable=False),
        sa.Column("physical_cores", sa.Integer(), nullable=True),
        sa.Column("logical_cores", sa.Integer(), nullable=True),
        sa.Column("system_ram_mb", sa.Integer(), nullable=False),
        sa.Column("available_ram_mb", sa.Integer(), nullable=False),
        sa.Column("os_name", sa.String(64), nullable=False),
        sa.Column("os_release", sa.String(64), nullable=False),
        sa.Column("architecture", sa.String(32), nullable=False),
        sa.Column("has_nvidia_gpu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gpu_info_json", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="MEASURED"),
        sa.Column("detection_limitations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_local_hw_snapshots_ws", "local_hardware_snapshots", ["workspace_id"])
    op.create_index("ix_local_hw_snapshots_user", "local_hardware_snapshots", ["user_id"])

    # 3. hardware_benchmarks
    op.create_table(
        "hardware_benchmarks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.String(36),
            sa.ForeignKey("local_hardware_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("benchmark_name", sa.String(128), nullable=False),
        sa.Column("benchmark_version", sa.String(32), nullable=False),
        sa.Column("workload_params_json", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("operations_per_second", sa.Float(), nullable=False),
        sa.Column("ram_before_mb", sa.Integer(), nullable=False),
        sa.Column("ram_after_mb", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="MEASURED"),
        sa.Column("status", sa.String(32), nullable=False, server_default="COMPLETED"),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_hw_benchmarks_ws", "hardware_benchmarks", ["workspace_id"])

    # 4. quantization_formats
    op.create_table(
        "quantization_formats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("format_key", sa.String(32), nullable=False, unique=True),
        sa.Column("format_family", sa.String(32), nullable=False),
        sa.Column("nominal_bits", sa.Float(), nullable=False),
        sa.Column("effective_reference_bits", sa.Float(), nullable=False),
        sa.Column("runtime_requirements_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_hardware_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("calculation_assumptions", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("registry_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_quant_formats_key", "quantization_formats", ["format_key"])

    # 5. resource_estimates
    op.create_table(
        "resource_estimates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("parameter_count_millions", sa.Float(), nullable=False),
        sa.Column("quantization_format", sa.String(32), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("execution_mode", sa.String(32), nullable=False),
        sa.Column("hardware_profile_key", sa.String(64), nullable=False),
        sa.Column("weight_memory_mb", sa.Float(), nullable=False),
        sa.Column("artifact_size_mb", sa.Float(), nullable=False),
        sa.Column("kv_cache_memory_mb", sa.Float(), nullable=False),
        sa.Column("runtime_overhead_mb", sa.Float(), nullable=False),
        sa.Column("peak_memory_mb", sa.Float(), nullable=False),
        sa.Column("available_memory_mb", sa.Float(), nullable=False),
        sa.Column("headroom_mb", sa.Float(), nullable=False),
        sa.Column("feasibility_status", sa.String(32), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="ESTIMATED"),
        sa.Column("calculation_details_json", sa.Text(), nullable=False),
        sa.Column("assumptions_and_warnings_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_res_estimates_ws", "resource_estimates", ["workspace_id"])

    # 6. pricing_catalog_entries
    op.create_table(
        "pricing_catalog_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_name", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("instance_type", sa.String(64), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("hourly_rate", sa.String(32), nullable=False),
        sa.Column("storage_monthly_rate_per_gb", sa.String(32), nullable=True),
        sa.Column("billing_unit_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("provenance", sa.String(32), nullable=False, server_default="REFERENCE_ONLY"),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catalog_version", sa.String(32), nullable=False, server_default="2026.1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "provider_name",
            "resource_type",
            "instance_type",
            "region",
            "catalog_version",
            name="uq_pricing_entry_resource_region_version",
        ),
    )
    op.create_index("ix_pricing_provider_resource", "pricing_catalog_entries", ["provider_name", "resource_type"])

    # 7. gate2_approval_requests
    op.create_table(
        "gate2_approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requester_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("workload_type", sa.String(64), nullable=False),
        sa.Column(
            "dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "gate1_approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "experiment_id",
            sa.String(36),
            sa.ForeignKey("experiments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("hardware_profile_key", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(64), nullable=False),
        sa.Column("instance_type", sa.String(64), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
        sa.Column("max_duration_hours", sa.Float(), nullable=False),
        sa.Column("estimated_compute_cost", sa.String(32), nullable=False),
        sa.Column("estimated_storage_cost", sa.String(32), nullable=False, server_default="0.00"),
        sa.Column("estimated_total_cost", sa.String(32), nullable=False),
        sa.Column("max_authorized_budget", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("proposal_digest", sa.String(64), nullable=False),
        sa.Column("proposal_payload_json", sa.Text(), nullable=False),
        sa.Column("pricing_snapshot_json", sa.Text(), nullable=False),
        sa.Column("pricing_catalog_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column(
            "approver_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approver_role_snapshot", sa.String(64), nullable=True),
        sa.Column("approval_signature", sa.String(256), nullable=True),
        sa.Column("signing_key_id", sa.String(64), nullable=True),
        sa.Column("signed_payload", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column(
            "revoked_by_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_gate2_req_ws", "gate2_approval_requests", ["workspace_id"])
    op.create_index("ix_gate2_req_status", "gate2_approval_requests", ["status"])
    op.create_index("ix_gate2_req_digest", "gate2_approval_requests", ["proposal_digest"])

    # 8. gate2_approval_events
    op.create_table(
        "gate2_approval_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "approval_request_id",
            sa.String(36),
            sa.ForeignKey("gate2_approval_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_gate2_events_req", "gate2_approval_events", ["approval_request_id"])

    # Seed Default Hardware Profiles (4 approved profiles)
    hw_table = sa.table(
        "hardware_profiles",
        sa.column("id", sa.String),
        sa.column("profile_key", sa.String),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("evidence_type", sa.String),
        sa.column("description", sa.String),
        sa.column("cpu_manufacturer", sa.String),
        sa.column("cpu_model", sa.String),
        sa.column("physical_cores", sa.Integer),
        sa.column("logical_cores", sa.Integer),
        sa.column("system_ram_mb", sa.Integer),
        sa.column("available_ram_mb", sa.Integer),
        sa.column("gpu_vendor", sa.String),
        sa.column("gpu_model", sa.String),
        sa.column("gpu_vram_mb", sa.Integer),
        sa.column("memory_bandwidth_gbps", sa.Float),
        sa.column("supported_numeric_precisions_json", sa.String),
        sa.column("supported_runtimes_json", sa.String),
        sa.column("supported_quantizations_json", sa.String),
        sa.column("supports_cpu_inference", sa.Boolean),
        sa.column("supports_gpu_inference", sa.Boolean),
        sa.column("supports_fine_tuning", sa.Boolean),
        sa.column("source_url", sa.String),
        sa.column("reference_date", sa.String),
        sa.column("limitations", sa.String),
        sa.column("is_reference", sa.Boolean),
    )

    op.bulk_insert(
        hw_table,
        [
            {
                "id": "hw-prof-local-cpu",
                "profile_key": "LOCAL_CPU_I5_8GB",
                "name": "Local Workstation (Intel Core i5, 8 GB RAM)",
                "category": "LOCAL_WORKSTATION",
                "evidence_type": "MEASURED",
                "description": "User local development workstation with Intel Core i5 processor and 8 GB system RAM. No dedicated GPU.",
                "cpu_manufacturer": "Intel",
                "cpu_model": "Intel Core i5 (Detected at runtime)",
                "physical_cores": 4,
                "logical_cores": 8,
                "system_ram_mb": 8192,
                "available_ram_mb": 5120,  # Accounting for OS & background process overhead
                "gpu_vendor": None,
                "gpu_model": None,
                "gpu_vram_mb": 0,
                "memory_bandwidth_gbps": None,
                "supported_numeric_precisions_json": json.dumps(["FP32", "INT8", "INT4"]),
                "supported_runtimes_json": json.dumps(["ollama", "onnx", "mock", "llama.cpp"]),
                "supported_quantizations_json": json.dumps(["Q4_K_M", "Q8_0", "FP16"]),
                "supports_cpu_inference": True,
                "supports_gpu_inference": False,
                "supports_fine_tuning": False,
                "source_url": "local://workstation",
                "reference_date": "2026-11-08",
                "limitations": "Operating system and background services consume approx 3 GB RAM. Maximum single model footprint is ~5 GB.",
                "is_reference": True,
            },
            {
                "id": "hw-prof-cloud-small",
                "profile_key": "REFERENCE_CPU_2VCPU_4GB",
                "name": "Cloud Small CPU (2 vCPU, 4 GB RAM)",
                "category": "CLOUD_CPU",
                "evidence_type": "VENDOR_REFERENCE",
                "description": "Generic reference cloud instance with 2 virtual CPUs and 4 GB RAM. CPU-only execution.",
                "cpu_manufacturer": "Generic Cloud",
                "cpu_model": "x86_64 2 vCPU",
                "physical_cores": 2,
                "logical_cores": 2,
                "system_ram_mb": 4096,
                "available_ram_mb": 3072,
                "gpu_vendor": None,
                "gpu_model": None,
                "gpu_vram_mb": 0,
                "memory_bandwidth_gbps": None,
                "supported_numeric_precisions_json": json.dumps(["FP32", "INT8", "INT4"]),
                "supported_runtimes_json": json.dumps(["ollama", "onnx", "mock"]),
                "supported_quantizations_json": json.dumps(["Q4_K_M", "Q8_0"]),
                "supports_cpu_inference": True,
                "supports_gpu_inference": False,
                "supports_fine_tuning": False,
                "source_url": "https://mizan.internal/reference-specs",
                "reference_date": "2026-11-08",
                "limitations": "This is a generic reference hardware profile. Actual hosting capabilities must be confirmed separately.",
                "is_reference": True,
            },
            {
                "id": "hw-prof-nvidia-t4",
                "profile_key": "NVIDIA_T4_16GB",
                "name": "NVIDIA Tesla T4 (16 GB GDDR6)",
                "category": "CLOUD_GPU",
                "evidence_type": "VENDOR_REFERENCE",
                "description": "NVIDIA Turing architecture datacenter GPU with 16 GB GDDR6 memory and Tensor Cores.",
                "cpu_manufacturer": "Generic Cloud",
                "cpu_model": "4 vCPU Host",
                "physical_cores": 4,
                "logical_cores": 4,
                "system_ram_mb": 16384,
                "available_ram_mb": 14336,
                "gpu_vendor": "NVIDIA",
                "gpu_model": "Tesla T4",
                "gpu_vram_mb": 16384,
                "memory_bandwidth_gbps": 320.0,
                "supported_numeric_precisions_json": json.dumps(["FP32", "FP16", "INT8", "INT4"]),
                "supported_runtimes_json": json.dumps(["ollama", "vllm", "tgi", "onnx", "mock"]),
                "supported_quantizations_json": json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
                "supports_cpu_inference": True,
                "supports_gpu_inference": True,
                "supports_fine_tuning": True,
                "source_url": "https://www.nvidia.com/en-in/data-center/tesla-t4/",
                "reference_date": "2026-11-08",
                "limitations": "16 GB VRAM bounds larger models. Memory bandwidth of 320 GB/s limits high-concurrency throughput.",
                "is_reference": True,
            },
            {
                "id": "hw-prof-nvidia-a100-40",
                "profile_key": "NVIDIA_A100_40GB",
                "name": "NVIDIA A100 Tensor Core GPU (40 GB HBM2)",
                "category": "CLOUD_GPU",
                "evidence_type": "VENDOR_REFERENCE",
                "description": "NVIDIA Ampere architecture flagship datacenter GPU with 40 GB high-bandwidth HBM2 memory (1,555 GB/s).",
                "cpu_manufacturer": "Generic Cloud",
                "cpu_model": "8 vCPU Host",
                "physical_cores": 8,
                "logical_cores": 8,
                "system_ram_mb": 65536,
                "available_ram_mb": 61440,
                "gpu_vendor": "NVIDIA",
                "gpu_model": "A100-PCIE-40GB",
                "gpu_vram_mb": 40960,
                "memory_bandwidth_gbps": 1555.0,
                "supported_numeric_precisions_json": json.dumps(["FP32", "TF32", "FP16", "BF16", "INT8", "INT4"]),
                "supported_runtimes_json": json.dumps(["ollama", "vllm", "tgi", "deepspeed", "mock"]),
                "supported_quantizations_json": json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
                "supports_cpu_inference": True,
                "supports_gpu_inference": True,
                "supports_fine_tuning": True,
                "source_url": "https://www.nvidia.com/en-in/data-center/a100/",
                "reference_date": "2026-11-08",
                "limitations": "Explicitly the 40 GB variant (not 80 GB). Suitable for medium-to-large parameter models and LoRA/full fine-tuning.",
                "is_reference": True,
            },
        ],
    )

    # Seed Quantization Formats (4 configurations)
    quant_table = sa.table(
        "quantization_formats",
        sa.column("id", sa.String),
        sa.column("format_key", sa.String),
        sa.column("format_family", sa.String),
        sa.column("nominal_bits", sa.Float),
        sa.column("effective_reference_bits", sa.Float),
        sa.column("runtime_requirements_json", sa.String),
        sa.column("supported_hardware_json", sa.String),
        sa.column("calculation_assumptions", sa.String),
        sa.column("limitations", sa.String),
        sa.column("source_reference", sa.String),
        sa.column("registry_version", sa.String),
    )

    op.bulk_insert(
        quant_table,
        [
            {
                "id": "quant-fp16",
                "format_key": "FP16",
                "format_family": "FLOAT",
                "nominal_bits": 16.0,
                "effective_reference_bits": 16.0,
                "runtime_requirements_json": json.dumps(["pytorch", "ollama", "vllm", "tgi"]),
                "supported_hardware_json": json.dumps(["CPU", "GPU"]),
                "calculation_assumptions": "Exactly 16 bits (2.0 bytes) per parameter before container metadata.",
                "limitations": "Highest memory consumption among standard deployment formats. Demands modern GPU Tensor Cores or AVX-512 for optimal throughput.",
                "source_reference": "IEEE 754-2008 Standard",
                "registry_version": "1.0.0",
            },
            {
                "id": "quant-q8-0",
                "format_key": "Q8_0",
                "format_family": "GGUF",
                "nominal_bits": 8.0,
                "effective_reference_bits": 8.5,
                "runtime_requirements_json": json.dumps(["llama.cpp", "ollama"]),
                "supported_hardware_json": json.dumps(["CPU", "GPU"]),
                "calculation_assumptions": "Standard 8-bit GGUF quantization with 32-weight blocks. Effective ~8.5 bits/weight including block scales.",
                "limitations": "Minimal accuracy degradation relative to FP16. Memory savings limited to ~47% reduction.",
                "source_reference": "GGUF Specification (llama.cpp)",
                "registry_version": "1.0.0",
            },
            {
                "id": "quant-q4-k-m",
                "format_key": "Q4_K_M",
                "format_family": "GGUF",
                "nominal_bits": 4.0,
                "effective_reference_bits": 4.9,
                "runtime_requirements_json": json.dumps(["llama.cpp", "ollama"]),
                "supported_hardware_json": json.dumps(["CPU", "GPU"]),
                "calculation_assumptions": "k-quantization medium scheme: uses 4.5 to 5.5 bits per tensor layer; average effective reference 4.9 bits/weight.",
                "limitations": "Slight perplexity increase on complex multi-hop reasoning. Ideal sweet spot for 8 GB RAM local deployment.",
                "source_reference": "llama.cpp k-quants PR #1684",
                "registry_version": "1.0.0",
            },
            {
                "id": "quant-awq",
                "format_key": "AWQ",
                "format_family": "AWQ",
                "nominal_bits": 4.0,
                "effective_reference_bits": 4.5,
                "runtime_requirements_json": json.dumps(["vllm", "tgi", "transformers"]),
                "supported_hardware_json": json.dumps(["GPU"]),
                "calculation_assumptions": "Activation-aware Weight Quantization with 128-weight grouping. Nominal 4-bit weights with scale/zero overhead yields ~4.5 bits.",
                "limitations": "Strictly GPU only. Not supported on CPU runtimes or GGUF executors. Requires CUDA Compute Capability >= 7.5.",
                "source_reference": "Lin et al., AWQ: Activation-aware Weight Quantization for LLM Compression (2023)",
                "registry_version": "1.0.0",
            },
        ],
    )

    # Seed Default Reference Pricing Entries
    pricing_table = sa.table(
        "pricing_catalog_entries",
        sa.column("id", sa.String),
        sa.column("provider_name", sa.String),
        sa.column("resource_type", sa.String),
        sa.column("instance_type", sa.String),
        sa.column("region", sa.String),
        sa.column("currency", sa.String),
        sa.column("hourly_rate", sa.String),
        sa.column("storage_monthly_rate_per_gb", sa.String),
        sa.column("billing_unit_seconds", sa.Integer),
        sa.column("source_url", sa.String),
        sa.column("provenance", sa.String),
        sa.column("effective_from", sa.DateTime),
        sa.column("is_verified", sa.Boolean),
        sa.column("catalog_version", sa.String),
    )

    now = datetime.now(UTC)
    op.bulk_insert(
        pricing_table,
        [
            {
                "id": "price-local-cpu",
                "provider_name": "local",
                "resource_type": "COMPUTE_CPU",
                "instance_type": "LOCAL_CPU_I5_8GB",
                "region": "local",
                "currency": "USD",
                "hourly_rate": "0.0000",
                "storage_monthly_rate_per_gb": "0.0000",
                "billing_unit_seconds": 1,
                "source_url": "local://workstation",
                "provenance": "OFFICIAL_SOURCE",
                "effective_from": now,
                "is_verified": True,
                "catalog_version": "2026.1",
            },
            {
                "id": "price-ref-cloud-cpu",
                "provider_name": "reference_cloud",
                "resource_type": "COMPUTE_CPU",
                "instance_type": "REFERENCE_CPU_2VCPU_4GB",
                "region": "us-east-1",
                "currency": "USD",
                "hourly_rate": "0.0400",
                "storage_monthly_rate_per_gb": "0.0200",
                "billing_unit_seconds": 3600,
                "source_url": "https://mizan.internal/reference-pricing",
                "provenance": "REFERENCE_ONLY",
                "effective_from": now,
                "is_verified": False,
                "catalog_version": "2026.1",
            },
            {
                "id": "price-ref-nvidia-t4",
                "provider_name": "reference_cloud",
                "resource_type": "COMPUTE_GPU",
                "instance_type": "NVIDIA_T4_16GB",
                "region": "us-east-1",
                "currency": "USD",
                "hourly_rate": "0.5260",
                "storage_monthly_rate_per_gb": "0.0200",
                "billing_unit_seconds": 3600,
                "source_url": "https://mizan.internal/reference-pricing",
                "provenance": "REFERENCE_ONLY",
                "effective_from": now,
                "is_verified": False,
                "catalog_version": "2026.1",
            },
            {
                "id": "price-ref-nvidia-a100",
                "provider_name": "reference_cloud",
                "resource_type": "COMPUTE_GPU",
                "instance_type": "NVIDIA_A100_40GB",
                "region": "us-east-1",
                "currency": "USD",
                "hourly_rate": "3.0600",
                "storage_monthly_rate_per_gb": "0.0200",
                "billing_unit_seconds": 3600,
                "source_url": "https://mizan.internal/reference-pricing",
                "provenance": "REFERENCE_ONLY",
                "effective_from": now,
                "is_verified": False,
                "catalog_version": "2026.1",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("gate2_approval_events")
    op.drop_table("gate2_approval_requests")
    op.drop_table("pricing_catalog_entries")
    op.drop_table("resource_estimates")
    op.drop_table("quantization_formats")
    op.drop_table("hardware_benchmarks")
    op.drop_table("local_hardware_snapshots")
    op.drop_table("hardware_profiles")
