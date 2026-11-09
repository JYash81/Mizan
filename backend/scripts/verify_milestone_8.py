"""Milestone 8 Verification and Local Demonstration Script.

Executes Demonstrations A through E with full output logging.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Ensure backend root is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.models.hardware import (
    EvidenceType,
    HardwareProfile,
    HardwareProfileCategory,
    PricingCatalogEntry,
    PricingProvenance,
)
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service
from app.modules.cost.cost_estimator import CostEstimatorService
from app.modules.cost.schemas.cost import CostEstimateRequest
from app.modules.gate2.approval_service import Gate2ApprovalService
from app.modules.gate2.financial_authorization import FinancialAuthorizationService
from app.modules.gate2.schemas.gate2 import (
    FinancialAuthorizationRequest,
    Gate2ApprovalRequestCreate,
    Gate2DecisionRequest,
)
from app.modules.hardware.benchmark_service import run_bounded_cpu_benchmark
from app.modules.hardware.compatibility_service import compare_workload_compatibility
from app.modules.hardware.hardware_detection import (
    detect_cpu_info,
    detect_memory_mb,
)
from app.modules.hardware.profile_registry import HardwareProfileRepository
from app.modules.hardware.quantization_registry import QuantizationRegistry
from app.modules.hardware.resource_estimator import estimate_model_resources
from app.modules.workspaces.services import organization_service, workspace_service


def run_demonstration():
    print("=" * 80)
    print("MIZAN MILESTONE 8: MASTER DEMONSTRATION & VERIFICATION")
    print("=" * 80)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    # Seed reference hardware profiles
    profiles = [
        HardwareProfile(
            profile_key="LOCAL_CPU_I5_8GB",
            name="Local Developer PC (Intel Core i5, 8 GB RAM)",
            category=HardwareProfileCategory.LOCAL_WORKSTATION,
            evidence_type=EvidenceType.MEASURED,
            cpu_manufacturer="Intel",
            cpu_model="Intel(R) Core(TM) i5-6500 CPU @ 3.20GHz",
            physical_cores=4,
            logical_cores=4,
            system_ram_mb=8109,
            available_ram_mb=5037,
            gpu_vram_mb=0,
            supported_numeric_precisions_json=json.dumps(["FP32", "INT8"]),
            supported_runtimes_json=json.dumps(["ollama", "onnx"]),
            supported_quantizations_json=json.dumps(["Q4_K_M", "Q8_0"]),
            supports_cpu_inference=True,
            supports_gpu_inference=False,
            supports_fine_tuning=False,
            limitations="Host is an 8 GB RAM quad-core workstation. FP16 causes paging.",
            is_reference=True,
        ),
        HardwareProfile(
            profile_key="REFERENCE_CPU_2VCPU_4GB",
            name="Reference Cloud CPU (2 vCPU, 4 GB RAM)",
            category=HardwareProfileCategory.CLOUD_CPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            cpu_manufacturer="Intel/AMD",
            cpu_model="General Purpose Cloud 2 vCPU",
            physical_cores=1,
            logical_cores=2,
            system_ram_mb=4096,
            available_ram_mb=3072,
            gpu_vram_mb=0,
            supported_numeric_precisions_json=json.dumps(["FP32", "INT8"]),
            supported_runtimes_json=json.dumps(["ollama"]),
            supported_quantizations_json=json.dumps(["Q4_K_M", "Q8_0"]),
            supports_cpu_inference=True,
            supports_gpu_inference=False,
            supports_fine_tuning=False,
            limitations="Cloud baseline for lightweight small-parameter CPU services.",
            is_reference=True,
        ),
        HardwareProfile(
            profile_key="NVIDIA_T4_16GB",
            name="NVIDIA T4 Tensor Core (16 GB VRAM)",
            category=HardwareProfileCategory.CLOUD_GPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            cpu_manufacturer="Intel Xeon",
            cpu_model="Cloud Host (4 vCPU, 15 GB RAM)",
            physical_cores=2,
            logical_cores=4,
            system_ram_mb=15360,
            available_ram_mb=14336,
            gpu_vendor="NVIDIA",
            gpu_model="Tesla T4",
            gpu_vram_mb=16384,
            supported_numeric_precisions_json=json.dumps(["FP32", "FP16", "INT8", "INT4"]),
            supported_runtimes_json=json.dumps(["vllm", "transformers"]),
            supported_quantizations_json=json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
            supports_cpu_inference=True,
            supports_gpu_inference=True,
            supports_fine_tuning=True,
            limitations="Entry accelerator. Limited memory bandwidth (320 GB/s).",
            is_reference=True,
        ),
        HardwareProfile(
            profile_key="NVIDIA_A100_40GB",
            name="NVIDIA A100 Tensor Core (40 GB VRAM)",
            category=HardwareProfileCategory.CLOUD_GPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            cpu_manufacturer="AMD EPYC",
            cpu_model="High-Memory Cloud Host (12 vCPU, 85 GB RAM)",
            physical_cores=6,
            logical_cores=12,
            system_ram_mb=87040,
            available_ram_mb=81920,
            gpu_vendor="NVIDIA",
            gpu_model="A100-PCIE-40GB",
            gpu_vram_mb=40960,
            supported_numeric_precisions_json=json.dumps(["FP32", "TF32", "FP16", "BF16", "INT8", "INT4"]),
            supported_runtimes_json=json.dumps(["vllm", "tgi", "transformers"]),
            supported_quantizations_json=json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
            supports_cpu_inference=True,
            supports_gpu_inference=True,
            supports_fine_tuning=True,
            limitations="High-end data center accelerator. Substantial hourly billing rate.",
            is_reference=True,
        ),
    ]
    db.add_all(profiles)

    # Seed pricing catalog
    now = datetime.now(UTC)
    pricing = [
        PricingCatalogEntry(
            provider_name="local",
            resource_type="WORKSTATION",
            instance_type="local-i5",
            region="local",
            currency="USD",
            hourly_rate="0.00",
            billing_unit_seconds=3600,
            provenance=PricingProvenance.OFFICIAL_SOURCE,
            effective_from=now,
            is_verified=True,
            catalog_version="2026.1",
        ),
        PricingCatalogEntry(
            provider_name="gcp",
            resource_type="GPU_VM",
            instance_type="n1-standard-4-t4-16gb",
            region="us-central1",
            currency="USD",
            hourly_rate="0.5260",
            billing_unit_seconds=3600,
            provenance=PricingProvenance.REFERENCE_ONLY,
            effective_from=now,
            is_verified=True,
            catalog_version="2026.1",
        ),
        PricingCatalogEntry(
            provider_name="gcp",
            resource_type="GPU_VM",
            instance_type="a2-highgpu-1g-a100-40gb",
            region="us-central1",
            currency="USD",
            hourly_rate="3.0600",
            billing_unit_seconds=3600,
            provenance=PricingProvenance.REFERENCE_ONLY,
            effective_from=now,
            is_verified=True,
            catalog_version="2026.1",
        ),
    ]
    db.add_all(pricing)

    # Create admin and test tenant
    admin = User(
        email="admin@mizan.org",
        normalized_email="admin@mizan.org",
        password_hash=password_service.hash_password("AdminPass123!"),
        full_name="Admin Reviewer",
        status=AccountStatus.ACTIVE,
    )
    db.add(admin)
    db.flush()

    org, _ = organization_service.create_organization(db, creator_id=admin.id, name="Mizan Demo Org", slug="mizan-demo-org")
    ws, _ = workspace_service.create_workspace(db, organization_id=org.id, creator_id=admin.id, name="AI Workspace", slug="ai-workspace")
    db.commit()

    # ------------------------------------------------------------------------
    # DEMONSTRATION A: Hardware Knowledge Base & Telemetry Verification
    # ------------------------------------------------------------------------
    print("\n--- DEMONSTRATION A: Hardware Knowledge Base & Host Telemetry ---")
    repo = HardwareProfileRepository()
    all_profs = repo.list_profiles(db)
    print(f"Total Reference Hardware Profiles Registered: {len(all_profs)}")
    for p in all_profs:
        print(f"  • [{p.profile_key}] {p.name}")
        print(f"    Category: {p.category.value} | Evidence: {p.evidence_type.value} | RAM: {p.system_ram_mb} MB | VRAM: {p.gpu_vram_mb} MB")

    cpu_model, phys, log = detect_cpu_info()
    tot_ram, avail_ram = detect_memory_mb()
    print("\nHost Hardware Inspection Telemetry:")
    print(f"  CPU Model: {cpu_model} ({phys} physical, {log} logical cores)")
    print(f"  System RAM: {tot_ram} MB total, {avail_ram} MB currently free")

    bench_res = run_bounded_cpu_benchmark(matrix_size=100, iterations=3)
    print(f"Safe CPU Benchmark Execution: Status={bench_res['status']}, Duration={bench_res['duration_ms']:.1f}ms, Throughput={bench_res['operations_per_second']/1e6:.2f} MFLOPS")

    # ------------------------------------------------------------------------
    # DEMONSTRATION B: Quantization & Resource Memory Estimator
    # ------------------------------------------------------------------------
    print("\n--- DEMONSTRATION B: Quantization & Resource Estimator Invariants ---")
    registry = QuantizationRegistry()
    formats = registry.list_formats()
    print("Registered Quantization Effective Bits:")
    for f in formats:
        print(f"  • {f.format_key}: {f.effective_reference_bits} bits/param ({f.format_family}) - Supported: {f.supported_hardware}")

    # Estimate 8B model across quantizations on Local CPU
    print("\nEvaluating 8B Model (Llama-3-8B) on Local CPU (8 GB RAM):")
    for q in ["FP16", "Q8_0", "Q4_K_M", "AWQ"]:
        est = estimate_model_resources(
            model_name="Llama-3-8B",
            parameter_count_millions=8000.0,
            quantization_format=q,
            context_length=2048,
            execution_mode="INFERENCE_CPU",
            hardware_profile={"profile_key": "LOCAL_CPU_I5_8GB", "system_ram_mb": 8109, "available_ram_mb": 5037},
        )
        print(f"  Format {q:<6}: Peak={est['peak_memory_mb']:>7.1f} MB | Headroom={est['headroom_mb']:>7.1f} MB | Feasibility={est['feasibility_status'].value}")

    # ------------------------------------------------------------------------
    # DEMONSTRATION C: Cross-Hardware Compatibility Matrix
    # ------------------------------------------------------------------------
    print("\n--- DEMONSTRATION C: Cross-Hardware Compatibility Matrix ---")
    comp_results = compare_workload_compatibility(
        db=db,
        model_name="Llama-3-8B",
        parameter_count_millions=8000.0,
        quantization_format="Q4_K_M",
        context_length=2048,
    )
    for c in comp_results:
        print(f"  • {c['profile_key']:<26}: Status={c['feasibility_status'].value:<18} | Req={c['required_ram_mb']+c['required_vram_mb']:>6.0f} MB | Avail={c['available_ram_mb']+c['available_vram_mb']:>6.0f} MB")
        print(f"    Reason: {c['reason']}")

    # ------------------------------------------------------------------------
    # DEMONSTRATION D: Pricing Catalog & Decimal Precision Cost Estimator
    # ------------------------------------------------------------------------
    print("\n--- DEMONSTRATION D: Pricing Catalog & Decimal Precision Cost Estimator ---")
    cost_svc = CostEstimatorService()

    local_cost = cost_svc.calculate_cost(
        db,
        CostEstimateRequest(provider_name="local", instance_type="local-i5", region="local", duration_hours=4.0),
    )
    print(f"  Local Workstation 4.0h Cost: ${local_cost.total_estimated_cost} (Status: {local_cost.status})")

    cloud_cost = cost_svc.calculate_cost(
        db,
        CostEstimateRequest(provider_name="gcp", instance_type="n1-standard-4-t4-16gb", region="us-central1", duration_hours=2.5),
    )
    print(f"  GCP T4 2.5h (3.0 billable hours) Cost: ${cloud_cost.total_estimated_cost} (Rate: $0.526/hr, Rounding: ROUND_HALF_UP)")

    missing_cost = cost_svc.calculate_cost(
        db,
        CostEstimateRequest(provider_name="nonexistent_cloud", instance_type="gpu-x", region="eu-west-1", duration_hours=1.0),
    )
    print(f"  Missing Price Invariant Check: Status={missing_cost.status}, Total={missing_cost.total_estimated_cost}")

    # ------------------------------------------------------------------------
    # DEMONSTRATION E: Gate 2 Financial Approval & Fail-Closed Policy Check
    # ------------------------------------------------------------------------
    print("\n--- DEMONSTRATION E: Gate 2 Financial Approval & Fail-Closed Policy ---")
    settings = get_settings()
    print(f"  Current Global Configuration: allow_paid_compute = {settings.allow_paid_compute}")

    gate2_svc = Gate2ApprovalService()
    authz_svc = FinancialAuthorizationService(approval_service=gate2_svc)

    # 1. Local $0.00 Workload
    local_req = gate2_svc.create_request(
        db,
        organization_id=org.id,
        workspace_id=ws.id,
        requester_id=admin.id,
        data=Gate2ApprovalRequestCreate(
            title="Local Evaluation Run",
            purpose="Deterministic CPU evaluation test",
            workload_type="EXPERIMENT_EVALUATION",
            hardware_profile_key="LOCAL_CPU_I5_8GB",
            provider_name="local",
            instance_type="local-i5",
            region="local",
            estimated_duration_hours=2.0,
            max_duration_hours=3.0,
            max_authorized_budget=Decimal("0.00"),
        ),
    )
    print(f"  Gate 2 Request Created: ID={local_req.id[:8]}... Digest={local_req.proposal_digest[:16]}... Status={local_req.status.value}")

    approved_local = gate2_svc.decide_request(
        db,
        request_id=local_req.id,
        workspace_id=ws.id,
        actor_id=admin.id,
        actor_role="ADMIN",
        data=Gate2DecisionRequest(decision="APPROVE", decision_reason="Approved for local zero-spend run"),
    )
    print(f"  Request Digitally Signed: Signature={approved_local.approval_signature[:16]}... KeyID={approved_local.signing_key_id}")

    auth_local = authz_svc.authorize_execution(db, FinancialAuthorizationRequest(approval_request_id=approved_local.id))
    print(f"  Local Execution Authorization: Authorized={auth_local.authorized} | Status={auth_local.status.value} | Reason={auth_local.reason}")

    # 2. Cloud GPU Workload (A100 at $3.06/hr)
    cloud_req = gate2_svc.create_request(
        db,
        organization_id=org.id,
        workspace_id=ws.id,
        requester_id=admin.id,
        data=Gate2ApprovalRequestCreate(
            title="Cloud A100 Training Run",
            purpose="Train large model in GCP",
            workload_type="FINE_TUNING",
            hardware_profile_key="NVIDIA_A100_40GB",
            provider_name="gcp",
            instance_type="a2-highgpu-1g-a100-40gb",
            region="us-central1",
            estimated_duration_hours=10.0,
            max_duration_hours=12.0,
            max_authorized_budget=Decimal("50.00"),
        ),
    )
    approved_cloud = gate2_svc.decide_request(
        db,
        request_id=cloud_req.id,
        workspace_id=ws.id,
        actor_id=admin.id,
        actor_role="ADMIN",
        data=Gate2DecisionRequest(decision="APPROVE", decision_reason="Executive approval granted for cloud run"),
    )
    print(f"\n  Cloud A100 Request Signed: Est Cost=${approved_cloud.estimated_total_cost} | Budget Cap=${approved_cloud.max_authorized_budget}")

    auth_cloud = authz_svc.authorize_execution(db, FinancialAuthorizationRequest(approval_request_id=approved_cloud.id))
    print("  Cloud Execution Authorization (Fail-Closed Check):")
    print(f"    Authorized: {auth_cloud.authorized}")
    print(f"    Status:     {auth_cloud.status.value}")
    print(f"    Policy Allowed: {auth_cloud.policy_allowed}")
    print(f"    Reason:     {auth_cloud.reason}")

    print("\n" + "=" * 80)
    print("ALL MILESTONE 8 DEMONSTRATIONS COMPLETED WITH ZERO ERRORS!")
    print("=" * 80)


if __name__ == "__main__":
    run_demonstration()
