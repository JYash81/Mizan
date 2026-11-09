"""Comprehensive unit and integration tests for Milestone 8:
Hardware Knowledge Base, Resource Estimator, Cost Estimator & Gate 2 Financial Approval.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.gate2 import Gate2ApprovalStatus
from app.models.hardware import (
    EvidenceType,
    FeasibilityStatus,
    HardwareProfile,
    HardwareProfileCategory,
    PricingCatalogEntry,
    PricingProvenance,
)
from app.models.identity import AccountStatus, User
from app.models.organization import OrganizationRole, WorkspaceRole
from app.modules.auth.services import password_service, session_service
from app.modules.cost.cost_estimator import CostEstimatorService
from app.modules.cost.schemas.cost import CostEstimateRequest
from app.modules.gate2.approval_service import Gate2ApprovalService
from app.modules.gate2.financial_authorization import FinancialAuthorizationService
from app.modules.gate2.proposal_digest import compute_proposal_digest
from app.modules.gate2.schemas.gate2 import (
    FinancialAuthorizationRequest,
    Gate2ApprovalRequestCreate,
    Gate2DecisionRequest,
    Gate2RevokeRequest,
)
from app.modules.hardware.benchmark_service import run_bounded_cpu_benchmark
from app.modules.hardware.compatibility_service import compare_workload_compatibility
from app.modules.hardware.hardware_detection import (
    detect_cpu_info,
    detect_memory_mb,
    inspect_local_hardware,
)
from app.modules.hardware.profile_registry import HardwareProfileRepository
from app.modules.hardware.quantization_registry import (
    calculate_weight_bytes,
    get_quantization_info,
    is_quantization_supported,
)
from app.modules.hardware.resource_estimator import estimate_kv_cache_mb, estimate_model_resources
from app.modules.workspaces.services import organization_service, workspace_service


@pytest.fixture
def m8_test_env():
    """Setup in-memory database and test client with reference data for Milestone 8."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    def _override_get_db():
        db = Session(engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    # Seed reference hardware profiles
    with Session(engine) as db:
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
                cpu_frequency_mhz=3200.0,
                system_ram_mb=8109,
                available_ram_mb=5037,
                gpu_vendor=None,
                gpu_model=None,
                gpu_vram_mb=0,
                memory_bandwidth_gbps=34.1,
                supported_numeric_precisions_json=json.dumps(["FP32", "INT8", "INT4"]),
                supported_runtimes_json=json.dumps(["ollama", "onnx", "mock"]),
                supported_quantizations_json=json.dumps(["Q4_K_M", "Q8_0"]),
                supports_cpu_inference=True,
                supports_gpu_inference=False,
                supports_fine_tuning=False,
                limitations="Host is an 8 GB RAM dual/quad-core workstation without dedicated GPU. Heavy FP16 inference causes paging.",
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
                gpu_vendor=None,
                gpu_model=None,
                gpu_vram_mb=0,
                memory_bandwidth_gbps=25.0,
                supported_numeric_precisions_json=json.dumps(["FP32", "INT8"]),
                supported_runtimes_json=json.dumps(["ollama", "onnx"]),
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
                memory_bandwidth_gbps=320.0,
                supported_numeric_precisions_json=json.dumps(["FP32", "FP16", "INT8", "INT4"]),
                supported_runtimes_json=json.dumps(["vllm", "tgi", "transformers", "ollama"]),
                supported_quantizations_json=json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
                supports_cpu_inference=True,
                supports_gpu_inference=True,
                supports_fine_tuning=True,
                limitations="Cost-effective entry accelerator for inference and LoRA. Limited memory bandwidth (320 GB/s).",
                is_reference=True,
            ),
            HardwareProfile(
                profile_key="NVIDIA_A100_40GB",
                name="NVIDIA A100 Tensor Core (40 GB SXM4/PCIe)",
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
                memory_bandwidth_gbps=1555.0,
                supported_numeric_precisions_json=json.dumps(
                    ["FP32", "TF32", "FP16", "BF16", "INT8", "INT4"]
                ),
                supported_runtimes_json=json.dumps(["vllm", "tgi", "transformers", "deepspeed"]),
                supported_quantizations_json=json.dumps(["FP16", "Q8_0", "Q4_K_M", "AWQ"]),
                supports_cpu_inference=True,
                supports_gpu_inference=True,
                supports_fine_tuning=True,
                limitations="High-end data center accelerator. Substantial hourly billing rate.",
                is_reference=True,
            ),
        ]
        db.add_all(profiles)

        # Seed reference pricing catalog
        now = datetime.now(UTC)
        pricing_entries = [
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
                provider_name="reference-cloud",
                resource_type="CPU_VM",
                instance_type="c6i.large",
                region="us-east-1",
                currency="USD",
                hourly_rate="0.0400",
                billing_unit_seconds=3600,
                provenance=PricingProvenance.REFERENCE_ONLY,
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
        db.add_all(pricing_entries)

        # Create test users and organization
        user_admin = User(
            email="admin@mizan.org",
            normalized_email="admin@mizan.org",
            password_hash=password_service.hash_password("AdminPass123!"),
            full_name="Admin Reviewer",
            status=AccountStatus.ACTIVE,
        )
        user_member = User(
            email="member@mizan.org",
            normalized_email="member@mizan.org",
            password_hash=password_service.hash_password("MemberPass123!"),
            full_name="Regular Developer",
            status=AccountStatus.ACTIVE,
        )
        db.add_all([user_admin, user_member])
        db.flush()

        org, _ = organization_service.create_organization(
            db, creator_id=user_admin.id, name="Mizan Test Org", slug="mizan-test-org"
        )
        organization_service.add_organization_member(
            db,
            organization_id=org.id,
            user_id=user_member.id,
            role=OrganizationRole.MEMBER,
        )

        ws1, _ = workspace_service.create_workspace(
            db,
            organization_id=org.id,
            creator_id=user_admin.id,
            name="Workspace Alpha",
            slug="workspace-alpha",
        )
        ws2, _ = workspace_service.create_workspace(
            db,
            organization_id=org.id,
            creator_id=user_admin.id,
            name="Workspace Beta",
            slug="workspace-beta",
        )
        workspace_service.add_workspace_member(
            db,
            workspace_id=ws1.id,
            user_id=user_member.id,
            role=WorkspaceRole.WORKSPACE_MEMBER,
            actor_id=user_admin.id,
        )

        admin_sess = session_service.create_session(db, user_admin.id)
        member_sess = session_service.create_session(db, user_member.id)
        db.commit()

        admin_id = user_admin.id
        member_id = user_member.id
        org_id = org.id
        ws1_id = ws1.id
        ws2_id = ws2.id

    return {
        "engine": engine,
        "client": client,
        "admin_id": admin_id,
        "member_id": member_id,
        "org_id": org_id,
        "ws1_id": ws1_id,
        "ws2_id": ws2_id,
        "admin_cookies": {"mizan_session": admin_sess.session_token},
        "admin_headers": {"X-CSRF-Token": admin_sess.csrf_token},
        "member_cookies": {"mizan_session": member_sess.session_token},
        "member_headers": {"X-CSRF-Token": member_sess.csrf_token},
    }


# ============================================================================
# 1. HARDWARE KNOWLEDGE BASE & DETECTION TESTS
# ============================================================================


def test_hardware_profiles_seeded(m8_test_env):
    """Verify that all 4 required reference hardware profiles are properly seeded."""
    with Session(m8_test_env["engine"]) as db:
        repo = HardwareProfileRepository()
        profiles = repo.list_profiles(db)
        keys = {p.profile_key for p in profiles}

        assert "LOCAL_CPU_I5_8GB" in keys
        assert "REFERENCE_CPU_2VCPU_4GB" in keys
        assert "NVIDIA_T4_16GB" in keys
        assert "NVIDIA_A100_40GB" in keys

        local_p = repo.get_by_key(db, "LOCAL_CPU_I5_8GB")
        assert local_p is not None
        assert local_p.evidence_type == EvidenceType.MEASURED
        assert local_p.supports_cpu_inference is True
        assert local_p.supports_gpu_inference is False
        assert local_p.system_ram_mb == 8109

        a100_p = repo.get_by_key(db, "NVIDIA_A100_40GB")
        assert a100_p is not None
        assert a100_p.gpu_vram_mb == 40960
        assert a100_p.evidence_type == EvidenceType.VENDOR_REFERENCE


def test_safe_local_hardware_detection():
    """Verify local detection runs safely without raising exceptions or requiring drivers."""
    cpu_model, phys, log = detect_cpu_info()
    assert isinstance(cpu_model, str)
    assert len(cpu_model) > 0
    assert log is not None and log >= 1

    total_ram, avail_ram = detect_memory_mb()
    assert total_ram > 0
    assert avail_ram > 0

    snapshot = inspect_local_hardware()
    assert snapshot["cpu_model"] == cpu_model
    assert snapshot["system_ram_mb"] == total_ram
    assert snapshot["evidence_type"] == EvidenceType.MEASURED
    assert "has_nvidia_gpu" in snapshot
    assert "os_name" in snapshot


def test_safe_bounded_cpu_benchmark():
    """Verify benchmark runs bounded workload, completes within timeout, and tracks RAM."""
    res = run_bounded_cpu_benchmark(matrix_size=50, iterations=2)
    assert res["status"] == "COMPLETED"
    assert res["duration_ms"] > 0
    assert res["operations_per_second"] > 0
    assert res["ram_before_mb"] > 0
    assert res["ram_after_mb"] > 0
    assert res["evidence_type"] == EvidenceType.MEASURED


# ============================================================================
# 2. QUANTIZATION & RESOURCE ESTIMATOR TESTS
# ============================================================================


def test_quantization_formulas():
    """Verify quantization effective bit formulas and calculation accuracy."""
    assert is_quantization_supported("FP16")
    assert is_quantization_supported("Q8_0")
    assert is_quantization_supported("Q4_K_M")
    assert is_quantization_supported("AWQ")
    assert not is_quantization_supported("UNSUPPORTED_FORMAT")

    assert get_quantization_info("FP16")["effective_reference_bits"] == 16.0
    assert get_quantization_info("Q8_0")["effective_reference_bits"] == 8.5
    assert get_quantization_info("Q4_K_M")["effective_reference_bits"] == 4.9
    assert get_quantization_info("AWQ")["effective_reference_bits"] == 4.5

    # 1 Billion parameters weight memory
    # FP16: 1e9 * 16 / 8 = 2,000,000,000 bytes (~1907.35 MB)
    fp16_bytes = calculate_weight_bytes(1_000_000_000, "FP16")
    assert fp16_bytes == 2_000_000_000

    # Q4_K_M: 1e9 * 4.9 / 8 = 612,500,000 bytes (~584.12 MB)
    q4_bytes = calculate_weight_bytes(1_000_000_000, "Q4_K_M")
    assert q4_bytes == 612_500_000


def test_kv_cache_calculation():
    """Verify architectural vs heuristic KV cache memory calculations."""
    # Architectural metadata: 32 layers, 8 kv heads, 128 head dim, 2048 ctx, batch 1
    # 2 * 32 * 8 * 128 * 2 * 2048 * 1 = 268,435,456 bytes = 256.0 MB
    kv_mb, method = estimate_kv_cache_mb(
        param_count=7_000_000_000,
        context_length=2048,
        batch_size=1,
        num_layers=32,
        num_kv_heads=8,
        head_dim=128,
    )
    assert method == "ARCHITECTURAL_METADATA"
    assert kv_mb == 256.0

    # Fallback heuristic
    kv_heur_mb, heur_method = estimate_kv_cache_mb(
        param_count=7_000_000_000,
        context_length=2048,
        batch_size=1,
    )
    assert heur_method == "HEURISTIC_FALLBACK"
    assert kv_heur_mb > 0.0


def test_resource_estimator_feasibility_rules():
    """Verify feasibility status determination and GPU-only / memory constraint invariants."""
    # 1. AWQ on CPU must be NOT_FEASIBLE
    est_awq_cpu = estimate_model_resources(
        model_name="test-model",
        parameter_count_millions=1000.0,
        quantization_format="AWQ",
        context_length=2048,
        execution_mode="INFERENCE_CPU",
        hardware_profile={
            "profile_key": "LOCAL_CPU_I5_8GB",
            "system_ram_mb": 8109,
            "available_ram_mb": 5000,
        },
    )
    assert est_awq_cpu["feasibility_status"] == FeasibilityStatus.NOT_FEASIBLE
    assert any("strictly GPU-only" in w for w in est_awq_cpu["assumptions_and_warnings"])

    # 2. Q4_K_M 1B model on Local CPU (should be FEASIBLE)
    est_q4_cpu = estimate_model_resources(
        model_name="test-model-1b",
        parameter_count_millions=1000.0,
        quantization_format="Q4_K_M",
        context_length=2048,
        execution_mode="INFERENCE_CPU",
        hardware_profile={
            "profile_key": "LOCAL_CPU_I5_8GB",
            "system_ram_mb": 8109,
            "available_ram_mb": 5000,
        },
    )
    assert est_q4_cpu["feasibility_status"] == FeasibilityStatus.FEASIBLE_ESTIMATE
    assert est_q4_cpu["headroom_mb"] > 0

    # 3. 70B model on Local CPU (insufficient memory, must be NOT_FEASIBLE)
    est_70b_cpu = estimate_model_resources(
        model_name="test-model-70b",
        parameter_count_millions=70000.0,
        quantization_format="Q4_K_M",
        context_length=2048,
        execution_mode="INFERENCE_CPU",
        hardware_profile={
            "profile_key": "LOCAL_CPU_I5_8GB",
            "system_ram_mb": 8109,
            "available_ram_mb": 5000,
        },
    )
    assert est_70b_cpu["feasibility_status"] == FeasibilityStatus.NOT_FEASIBLE
    assert est_70b_cpu["headroom_mb"] < -512.0


def test_cross_profile_compatibility(m8_test_env):
    """Verify workload compatibility matrix across all 4 reference profiles."""
    with Session(m8_test_env["engine"]) as db:
        results = compare_workload_compatibility(
            db=db,
            model_name="llama-3-8b",
            parameter_count_millions=8000.0,
            quantization_format="Q4_K_M",
            context_length=2048,
        )
        assert len(results) == 4
        keys = {r["profile_key"] for r in results}
        assert "LOCAL_CPU_I5_8GB" in keys
        assert "NVIDIA_T4_16GB" in keys
        assert "NVIDIA_A100_40GB" in keys


# ============================================================================
# 3. COST ESTIMATION & PRICING TESTS
# ============================================================================


def test_decimal_precision_cost_estimator(m8_test_env):
    """Verify Decimal arithmetic prevents floating-point inaccuracies and billing-unit rounds up."""
    with Session(m8_test_env["engine"]) as db:
        estimator = CostEstimatorService()

        # Local execution is strictly $0.00
        local_req = CostEstimateRequest(
            provider_name="local",
            instance_type="local-i5",
            region="local",
            duration_hours=5.5,
        )
        local_resp = estimator.calculate_cost(db, local_req)
        assert local_resp.status == "ZERO_SPEND_LOCAL"
        assert local_resp.total_estimated_cost == "0.00"

        # GCP T4 calculation: duration 2.5 hours rounded up to 3 hours at $0.526/hour
        # 3 * 0.526 = 1.578 -> rounded to 1.58
        t4_req = CostEstimateRequest(
            provider_name="gcp",
            instance_type="n1-standard-4-t4-16gb",
            region="us-central1",
            duration_hours=2.5,
        )
        t4_resp = estimator.calculate_cost(db, t4_req)
        assert t4_resp.status == "AVAILABLE"
        assert t4_resp.billable_hours == 3.0
        assert t4_resp.total_estimated_cost == "1.58"

        # Missing price record must return PRICE_UNAVAILABLE (Strict Invariant: never default to 0.0)
        missing_req = CostEstimateRequest(
            provider_name="unknown_cloud",
            instance_type="nonexistent-gpu",
            region="antarctica",
            duration_hours=1.0,
        )
        missing_resp = estimator.calculate_cost(db, missing_req)
        assert missing_resp.status == "PRICE_UNAVAILABLE"
        assert missing_resp.total_estimated_cost == "UNKNOWN"


# ============================================================================
# 4. GATE 2 FINANCIAL APPROVAL & FAIL-CLOSED POLICY TESTS
# ============================================================================


def test_gate2_approval_workflow_and_attestation(m8_test_env):
    """Test Gate 2 request creation, deterministic digest, Ed25519 signing, and anti-tamper verification."""
    with Session(m8_test_env["engine"]) as db:
        svc = Gate2ApprovalService()
        authz_svc = FinancialAuthorizationService(approval_service=svc)

        # 1. Create request
        req_data = Gate2ApprovalRequestCreate(
            title="Model Evaluation Run on Local CPU",
            purpose="Run automated evaluation suite on local hardware",
            workload_type="EXPERIMENT_EVALUATION",
            hardware_profile_key="LOCAL_CPU_I5_8GB",
            provider_name="local",
            instance_type="local-i5",
            region="local",
            estimated_duration_hours=2.0,
            max_duration_hours=4.0,
            max_authorized_budget=Decimal("0.00"),
        )
        req = svc.create_request(
            db,
            organization_id=m8_test_env["org_id"],
            workspace_id=m8_test_env["ws1_id"],
            requester_id=m8_test_env["member_id"],
            data=req_data,
        )
        assert req.status == Gate2ApprovalStatus.PENDING_APPROVAL
        assert req.estimated_total_cost == "0.00"
        assert len(req.proposal_digest) == 64
        assert len(req.events) == 1

        # 2. Approve request with Ed25519 digital signature
        decision_data = Gate2DecisionRequest(
            decision="APPROVE",
            decision_reason="Approved for local zero-cost experimentation.",
        )
        approved_req = svc.decide_request(
            db,
            request_id=req.id,
            workspace_id=m8_test_env["ws1_id"],
            actor_id=m8_test_env["admin_id"],
            actor_role="ADMIN",
            data=decision_data,
        )
        assert approved_req.status == Gate2ApprovalStatus.APPROVED
        assert approved_req.approval_signature is not None
        assert approved_req.signed_payload is not None
        assert len(approved_req.events) == 2

        # 3. Check financial authorization on valid local workload
        auth_req = FinancialAuthorizationRequest(
            approval_request_id=approved_req.id,
            proposed_cost=Decimal("0.00"),
        )
        auth_resp = authz_svc.authorize_execution(db, req=auth_req)
        assert auth_resp.authorized is True
        assert auth_resp.status == Gate2ApprovalStatus.APPROVED
        assert auth_resp.proposal_digest_match is True
        assert auth_resp.signature_valid is True
        assert auth_resp.policy_allowed is True


def test_gate2_anti_tampering_and_revocation(m8_test_env):
    """Verify that tampering with proposal payload or revoking invalidates execution."""
    with Session(m8_test_env["engine"]) as db:
        svc = Gate2ApprovalService()
        authz_svc = FinancialAuthorizationService(approval_service=svc)

        req_data = Gate2ApprovalRequestCreate(
            title="Local Run",
            purpose="Experimentation",
            hardware_profile_key="LOCAL_CPU_I5_8GB",
            provider_name="local",
            instance_type="local-i5",
            region="local",
            estimated_duration_hours=1.0,
            max_duration_hours=2.0,
            max_authorized_budget=Decimal("0.00"),
        )
        req = svc.create_request(
            db,
            organization_id=m8_test_env["org_id"],
            workspace_id=m8_test_env["ws1_id"],
            requester_id=m8_test_env["member_id"],
            data=req_data,
        )
        svc.decide_request(
            db,
            request_id=req.id,
            workspace_id=m8_test_env["ws1_id"],
            actor_id=m8_test_env["admin_id"],
            actor_role="ADMIN",
            data=Gate2DecisionRequest(
                decision="APPROVE", decision_reason="Approved for anti-tamper verification"
            ),
        )

        # Tampering test: alter the saved payload json in the database
        req.proposal_payload_json = req.proposal_payload_json.replace("Local Run", "Tampered Run")
        db.commit()

        tampered_auth = authz_svc.authorize_execution(
            db, req=FinancialAuthorizationRequest(approval_request_id=req.id)
        )
        assert tampered_auth.authorized is False
        assert tampered_auth.status == Gate2ApprovalStatus.INVALIDATED
        assert "integrity failure" in tampered_auth.reason

        # Revert payload, now test Revocation
        canonical_json, digest = compute_proposal_digest(
            json.loads(req.proposal_payload_json.replace("Tampered Run", "Local Run"))
        )
        req.proposal_payload_json = canonical_json
        req.proposal_digest = digest
        db.commit()

        svc.revoke_request(
            db,
            request_id=req.id,
            workspace_id=m8_test_env["ws1_id"],
            actor_id=m8_test_env["admin_id"],
            data=Gate2RevokeRequest(revocation_reason="Budget reallocation"),
        )
        revoked_auth = authz_svc.authorize_execution(
            db, req=FinancialAuthorizationRequest(approval_request_id=req.id)
        )
        assert revoked_auth.authorized is False
        assert revoked_auth.status == Gate2ApprovalStatus.REVOKED


def test_strict_global_free_only_policy_invariant(m8_test_env):
    """MANDATORY INVARIANT: When allow_paid_compute=False, a signed Gate 2 approval for
    paid cloud hardware is STRICTLY BLOCKED_BY_POLICY.
    """
    settings = get_settings()
    assert settings.allow_paid_compute is False, (
        "Safety invariant: default must disallow paid compute"
    )

    with Session(m8_test_env["engine"]) as db:
        svc = Gate2ApprovalService()
        authz_svc = FinancialAuthorizationService(approval_service=svc)

        # Create request for expensive cloud GPU (GCP A100 at $3.06/hour)
        cloud_req_data = Gate2ApprovalRequestCreate(
            title="Large Cloud Model Fine-Tuning",
            purpose="Train custom model on high-memory A100 GPU",
            workload_type="FINE_TUNING",
            hardware_profile_key="NVIDIA_A100_40GB",
            provider_name="gcp",
            instance_type="a2-highgpu-1g-a100-40gb",
            region="us-central1",
            estimated_duration_hours=10.0,
            max_duration_hours=12.0,
            max_authorized_budget=Decimal("50.00"),
        )
        cloud_req = svc.create_request(
            db,
            organization_id=m8_test_env["org_id"],
            workspace_id=m8_test_env["ws1_id"],
            requester_id=m8_test_env["member_id"],
            data=cloud_req_data,
        )
        assert cloud_req.estimated_total_cost == "30.60"

        # Admin signs and approves the budget
        svc.decide_request(
            db,
            request_id=cloud_req.id,
            workspace_id=m8_test_env["ws1_id"],
            actor_id=m8_test_env["admin_id"],
            actor_role="ADMIN",
            data=Gate2DecisionRequest(
                decision="APPROVE",
                decision_reason="Executive approval granted for cloud run.",
            ),
        )

        # Execution Authorization check MUST FAIL-CLOSED due to global free-only policy
        auth_resp = authz_svc.authorize_execution(
            db, req=FinancialAuthorizationRequest(approval_request_id=cloud_req.id)
        )
        assert auth_resp.authorized is False
        assert auth_resp.status == Gate2ApprovalStatus.BLOCKED_BY_POLICY
        assert auth_resp.signature_valid is True
        assert auth_resp.policy_allowed is False
        assert "allow_paid_compute=False" in auth_resp.reason


# ============================================================================
# 5. REST API ENDPOINT INTEGRATION TESTS
# ============================================================================


def test_hardware_profiles_api(m8_test_env):
    """Test GET /api/v1/workspaces/{ws_id}/hardware/profiles."""
    client = m8_test_env["client"]
    ws_id = m8_test_env["ws1_id"]
    res = client.get(
        f"/api/v1/workspaces/{ws_id}/hardware/profiles",
        cookies=m8_test_env["member_cookies"],
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    keys = {p["profile_key"] for p in data}
    assert "LOCAL_CPU_I5_8GB" in keys


def test_hardware_detect_and_quantization_api(m8_test_env):
    """Test POST hardware/detect and GET hardware/quantizations."""
    client = m8_test_env["client"]
    ws_id = m8_test_env["ws1_id"]

    # Detect hardware
    res_detect = client.post(
        f"/api/v1/workspaces/{ws_id}/hardware/detect",
        cookies=m8_test_env["member_cookies"],
    )
    assert res_detect.status_code == 200
    detect_data = res_detect.json()
    assert detect_data["system_ram_mb"] > 0
    assert detect_data["evidence_type"] == "MEASURED"

    # List quantizations
    res_quant = client.get(
        f"/api/v1/workspaces/{ws_id}/hardware/quantizations",
        cookies=m8_test_env["member_cookies"],
    )
    assert res_quant.status_code == 200
    quant_data = res_quant.json()
    formats = {q["format_key"] for q in quant_data}
    assert "FP16" in formats
    assert "Q4_K_M" in formats
    assert "AWQ" in formats


def test_resource_estimate_and_compare_api(m8_test_env):
    """Test POST hardware/estimate and POST hardware/compare."""
    client = m8_test_env["client"]
    ws_id = m8_test_env["ws1_id"]

    est_payload = {
        "model_name": "phi-3-mini",
        "parameter_count_millions": 3800.0,
        "quantization_format": "Q4_K_M",
        "context_length": 2048,
        "batch_size": 1,
        "execution_mode": "INFERENCE_CPU",
        "hardware_profile_key": "LOCAL_CPU_I5_8GB",
    }
    res_est = client.post(
        f"/api/v1/workspaces/{ws_id}/hardware/estimate",
        json=est_payload,
        cookies=m8_test_env["member_cookies"],
    )
    assert res_est.status_code == 200
    est_data = res_est.json()
    assert est_data["weight_memory_mb"] > 0
    assert est_data["peak_memory_mb"] > 0
    assert est_data["feasibility_status"] in ("FEASIBLE_ESTIMATE", "LIKELY_FEASIBLE")

    comp_payload = {
        "model_name": "phi-3-mini",
        "parameter_count_millions": 3800.0,
        "quantization_format": "Q4_K_M",
        "context_length": 2048,
        "batch_size": 1,
        "execution_mode": "INFERENCE_CPU",
    }
    res_comp = client.post(
        f"/api/v1/workspaces/{ws_id}/hardware/compare",
        json=comp_payload,
        cookies=m8_test_env["member_cookies"],
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert len(comp_data["profiles"]) == 4


def test_cost_and_gate2_api_lifecycle(m8_test_env):
    """Test full HTTP API lifecycle for Cost Estimation and Gate 2 Approval."""
    client = m8_test_env["client"]
    ws_id = m8_test_env["ws1_id"]

    # 1. Pricing list
    res_pricing = client.get(
        f"/api/v1/workspaces/{ws_id}/cost/pricing",
        cookies=m8_test_env["member_cookies"],
    )
    assert res_pricing.status_code == 200
    pricing_data = res_pricing.json()
    assert len(pricing_data) >= 4

    # 2. Cost estimate
    res_cost = client.post(
        f"/api/v1/workspaces/{ws_id}/cost/estimate",
        json={
            "provider_name": "local",
            "instance_type": "local-i5",
            "region": "local",
            "duration_hours": 3.0,
        },
        cookies=m8_test_env["member_cookies"],
    )
    assert res_cost.status_code == 200
    cost_data = res_cost.json()
    assert cost_data["total_estimated_cost"] == "0.00"

    # 3. Create Gate 2 Request
    req_payload = {
        "title": "API Test Workload",
        "purpose": "Verify Gate 2 HTTP workflow",
        "workload_type": "EXPERIMENT_EVALUATION",
        "hardware_profile_key": "LOCAL_CPU_I5_8GB",
        "provider_name": "local",
        "instance_type": "local-i5",
        "region": "local",
        "estimated_duration_hours": 2.0,
        "max_duration_hours": 3.0,
        "max_authorized_budget": "0.00",
    }
    res_create = client.post(
        f"/api/v1/workspaces/{ws_id}/gate2/requests",
        json=req_payload,
        cookies=m8_test_env["member_cookies"],
        headers=m8_test_env["member_headers"],
    )
    assert res_create.status_code == 201
    created_req = res_create.json()
    req_id = created_req["id"]
    assert created_req["status"] == "PENDING_APPROVAL"

    # 4. Decide (Approve) Gate 2 Request by Admin
    res_decide = client.post(
        f"/api/v1/workspaces/{ws_id}/gate2/requests/{req_id}/decide",
        json={
            "decision": "APPROVE",
            "decision_reason": "Approved via API integration test",
        },
        cookies=m8_test_env["admin_cookies"],
        headers=m8_test_env["admin_headers"],
    )
    assert res_decide.status_code == 200
    decided_data = res_decide.json()
    assert decided_data["status"] == "APPROVED"
    assert decided_data["approval_signature"] is not None

    # 5. Check Financial Authorization
    res_auth = client.post(
        f"/api/v1/workspaces/{ws_id}/gate2/authorize",
        json={"approval_request_id": req_id, "proposed_cost": "0.00"},
        cookies=m8_test_env["member_cookies"],
    )
    assert res_auth.status_code == 200
    auth_data = res_auth.json()
    assert auth_data["authorized"] is True
    assert auth_data["status"] == "APPROVED"
