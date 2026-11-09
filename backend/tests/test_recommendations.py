"""Comprehensive Automated Test Suite for Milestone 9:
Recommendation Engine, Multi-Objective Optimization, Pareto Analysis & Explainability.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.dataset import Dataset, DatasetStatus, DatasetVersion, DatasetVersionStatus
from app.models.evaluation import (
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationSuite,
    EvaluationSuiteStatus,
    EvaluationSuiteVersion,
    EvaluationTargetType,
    SplitType,
    SuiteVersionStatus,
)
from app.models.experiment import (
    Experiment,
    ExperimentStatus,
    ExperimentTrial,
    TrialStatus,
)
from app.models.hardware import (
    EvidenceType,
    HardwareProfile,
    HardwareProfileCategory,
)
from app.models.identity import AccountStatus, User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
    WorkspaceStatus,
)
from app.models.recommendations import (
    CandidateEligibilityStatus,
    CandidateProvenanceStatus,
    RecommendationDecisionType,
    RecommendationRunStatus,
)
from app.modules.auth.services import password_service, session_service
from app.modules.recommendations.comparability_service import ComparabilityService
from app.modules.recommendations.constraint_engine import ConstraintEngine
from app.modules.recommendations.explanation_engine import ExplanationEngine
from app.modules.recommendations.normalization_service import NormalizationService
from app.modules.recommendations.objective_registry import (
    ObjectiveRegistry,
    OptimizationDirection,
)
from app.modules.recommendations.pareto_engine import ParetoEngine
from app.modules.recommendations.recommendation_service import (
    compute_canonical_digest,
)
from app.modules.recommendations.sensitivity_analysis import SensitivityAnalysisEngine
from app.modules.recommendations.weighted_scoring import (
    PREFERENCE_PRESETS,
    WeightedScoringEngine,
)


@pytest.fixture
def m9_env():
    """Setup in-memory SQLite database and TestClient with complete M6-M9 fixtures."""
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

    with Session(engine, expire_on_commit=False) as db:
        # 1. Seed Reference Hardware Profile
        hw_local = HardwareProfile(
            profile_key="LOCAL_CPU_I5_8GB",
            name="Local PC (Core i5, 8 GB)",
            category=HardwareProfileCategory.LOCAL_WORKSTATION,
            evidence_type=EvidenceType.MEASURED,
            system_ram_mb=8109,
            supports_cpu_inference=True,
            is_reference=True,
        )
        hw_cloud_gpu = HardwareProfile(
            profile_key="NVIDIA_T4_16GB",
            name="NVIDIA T4 (16 GB VRAM)",
            category=HardwareProfileCategory.CLOUD_GPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            system_ram_mb=16384,
            gpu_vram_mb=16384,
            supports_cpu_inference=False,
            supports_gpu_inference=True,
            is_reference=True,
        )
        db.add_all([hw_local, hw_cloud_gpu])

        # 2. Seed Users
        user_owner = User(
            id="user-owner-1",
            email="owner@mizan.org",
            normalized_email="owner@mizan.org",
            full_name="Lead Architect",
            password_hash=password_service.hash_password("SuperSecret123!"),
            status=AccountStatus.ACTIVE,
            email_verified_at=datetime.now(UTC),
        )
        user_other = User(
            id="user-other-2",
            email="other@mizan.org",
            normalized_email="other@mizan.org",
            full_name="Other Tenant",
            password_hash=password_service.hash_password("SuperSecret123!"),
            status=AccountStatus.ACTIVE,
            email_verified_at=datetime.now(UTC),
        )
        db.add_all([user_owner, user_other])
        db.commit()

        # 3. Seed Organizations & Workspaces
        org_a = Organization(
            id="org-a",
            name="Mizan Org A",
            slug="mizan-org-a",
            status=OrganizationStatus.ACTIVE,
            created_by=user_owner.id,
        )
        org_b = Organization(
            id="org-b",
            name="Mizan Org B",
            slug="mizan-org-b",
            status=OrganizationStatus.ACTIVE,
            created_by=user_other.id,
        )
        db.add_all([org_a, org_b])

        ws_a = Workspace(
            id="ws-a",
            organization_id=org_a.id,
            name="Workspace A",
            slug="workspace-a",
            status=WorkspaceStatus.ACTIVE,
            created_by=user_owner.id,
        )
        ws_b = Workspace(
            id="ws-b",
            organization_id=org_b.id,
            name="Workspace B",
            slug="workspace-b",
            status=WorkspaceStatus.ACTIVE,
            created_by=user_other.id,
        )
        db.add_all([ws_a, ws_b])

        # Memberships
        db.add(OrganizationMembership(
            organization_id=org_a.id,
            user_id=user_owner.id,
            role=OrganizationRole.OWNER,
        ))
        db.add(WorkspaceMembership(
            workspace_id=ws_a.id,
            user_id=user_owner.id,
            role=WorkspaceRole.WORKSPACE_OWNER,
        ))
        db.add(OrganizationMembership(
            organization_id=org_b.id,
            user_id=user_other.id,
            role=OrganizationRole.OWNER,
        ))
        db.add(WorkspaceMembership(
            workspace_id=ws_b.id,
            user_id=user_other.id,
            role=WorkspaceRole.WORKSPACE_OWNER,
        ))
        db.commit()

        # 4. Seed Dataset & Version with Gate 1 reference
        ds = Dataset(
            id="ds-1",
            workspace_id=ws_a.id,
            name="Financial Reports",
            slug="financial-reports",
            status=DatasetStatus.ACTIVE,
            created_by=user_owner.id,
        )
        db.add(ds)
        db.commit()

        ds_v = DatasetVersion(
            id="ds-v-1",
            dataset_id=ds.id,
            version_number=1,
            name="v1",
            content_hash="sha256:dsv1hash",
            status=DatasetVersionStatus.READY,
        )
        db.add(ds_v)
        db.commit()

        # 5. Seed Frozen Evaluation Suite Version
        suite = EvaluationSuite(
            id="suite-1",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            name="Q4 Enterprise QA",
            slug="q4-enterprise-qa",
            status=EvaluationSuiteStatus.READY,
            created_by=user_owner.id,
        )
        db.add(suite)
        db.commit()

        suite_v = EvaluationSuiteVersion(
            id="suite-v-1",
            suite_id=suite.id,
            version_number=1,
            suite_digest="sha256:suitev1digest",
            case_count=10,
            status=SuiteVersionStatus.FINALIZED,
            created_by=user_owner.id,
        )
        db.add(suite_v)
        db.commit()

        # 6. Seed Completed Evaluation Runs
        eval_run_1 = EvaluationRun(
            id="eval-run-1",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            suite_id=suite.id,
            suite_version_id=suite_v.id,
            target_type=EvaluationTargetType.RAG_PIPELINE,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=92.5,
            created_by=user_owner.id,
        )
        eval_run_2 = EvaluationRun(
            id="eval-run-2",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            suite_id=suite.id,
            suite_version_id=suite_v.id,
            target_type=EvaluationTargetType.RAG_PIPELINE,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=85.0,
            created_by=user_owner.id,
        )
        eval_run_3 = EvaluationRun(
            id="eval-run-3",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            suite_id=suite.id,
            suite_version_id=suite_v.id,
            target_type=EvaluationTargetType.RAG_PIPELINE,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=78.0,
            created_by=user_owner.id,
        )
        db.add_all([eval_run_1, eval_run_2, eval_run_3])
        db.commit()

        # 7. Seed M7 Experiment & Controlled Trials
        exp = Experiment(
            id="exp-1",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            name="LLM RAG Optimization",
            slug="llm-rag-opt",
            status=ExperimentStatus.COMPLETED,
            dataset_id=ds.id,
            dataset_version_id=ds_v.id,
            gate1_approval_id="gate1-appr-1",
            evaluation_suite_id=suite.id,
            evaluation_suite_version_id=suite_v.id,
            canonical_suite_digest="sha256:suitev1digest",
            evaluation_split=SplitType.VALIDATION,
            total_trials=3,
            completed_trials=3,
            created_by=user_owner.id,
        )
        db.add(exp)
        db.commit()

        # Trial 1: High Quality, Moderate Latency
        trial_1 = ExperimentTrial(
            id="trial-1",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            experiment_id=exp.id,
            trial_number=1,
            name="Chunk 512 + Q4_K_M",
            status=TrialStatus.COMPLETED,
            configuration_json=json.dumps({
                "model_name": "qwen2.5-1.5b",
                "parameter_count_millions": 1540.0,
                "quantization_format": "Q4_K_M",
                "context_length": 2048,
                "hardware_profile_key": "LOCAL_CPU_I5_8GB",
            }),
            configuration_digest="sha256:t1digest",
            evaluation_run_id=eval_run_1.id,
            aggregate_score=92.5,
            score_breakdown_json=json.dumps({
                "exact_match": 91.0,
                "faithfulness": 94.0,
                "groundedness": 93.0,
                "citation_verification": 95.0,
                "safety": 98.0,
                "compliance": 100.0,
            }),
            latency_p50_ms=450.0,
            latency_p95_ms=850.0,
            latency_p99_ms=1100.0,
            execution_duration_ms=45000.0,
        )

        # Trial 2: Lower Quality, Ultra-Fast Latency
        trial_2 = ExperimentTrial(
            id="trial-2",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            experiment_id=exp.id,
            trial_number=2,
            name="Chunk 256 + Q4_K_M Fast",
            status=TrialStatus.COMPLETED,
            configuration_json=json.dumps({
                "model_name": "qwen2.5-0.5b",
                "parameter_count_millions": 490.0,
                "quantization_format": "Q4_K_M",
                "context_length": 1024,
                "hardware_profile_key": "LOCAL_CPU_I5_8GB",
            }),
            configuration_digest="sha256:t2digest",
            evaluation_run_id=eval_run_2.id,
            aggregate_score=85.0,
            score_breakdown_json=json.dumps({
                "exact_match": 82.0,
                "faithfulness": 86.0,
                "groundedness": 88.0,
                "citation_verification": 84.0,
                "safety": 95.0,
                "compliance": 99.0,
            }),
            latency_p50_ms=150.0,
            latency_p95_ms=320.0,
            latency_p99_ms=450.0,
            execution_duration_ms=18000.0,
        )

        # Trial 3: Dominated Candidate (Lower Quality than T1 and T2, Slower than T2)
        trial_3 = ExperimentTrial(
            id="trial-3",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            experiment_id=exp.id,
            trial_number=3,
            name="Sub-optimal FP16 Baseline",
            status=TrialStatus.COMPLETED,
            configuration_json=json.dumps({
                "model_name": "qwen2.5-0.5b",
                "parameter_count_millions": 490.0,
                "quantization_format": "FP16",
                "context_length": 2048,
                "hardware_profile_key": "LOCAL_CPU_I5_8GB",
            }),
            configuration_digest="sha256:t3digest",
            evaluation_run_id=eval_run_3.id,
            aggregate_score=78.0,
            score_breakdown_json=json.dumps({
                "exact_match": 75.0,
                "faithfulness": 80.0,
                "groundedness": 79.0,
                "citation_verification": 76.0,
                "safety": 92.0,
                "compliance": 95.0,
            }),
            latency_p50_ms=520.0,
            latency_p95_ms=980.0,
            latency_p99_ms=1300.0,
            execution_duration_ms=55000.0,
        )

        # Trial 4: Failed Trial (should be excluded by constraints)
        trial_failed = ExperimentTrial(
            id="trial-failed-4",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            experiment_id=exp.id,
            trial_number=4,
            name="Failed Run",
            status=TrialStatus.FAILED,
            configuration_json=json.dumps({
                "model_name": "invalid-model",
                "parameter_count_millions": 7000.0,
                "quantization_format": "FP16",
                "hardware_profile_key": "LOCAL_CPU_I5_8GB",
            }),
            configuration_digest="sha256:t4digest",
            error_summary="Out of memory",
        )

        db.add_all([trial_1, trial_2, trial_3, trial_failed])
        db.commit()

    # Session cookie for user_owner
    with Session(engine) as db:
        issued_session = session_service.create_session(
            db, user_id=user_owner.id
        )
        db.commit()

    client.cookies.set("mizan_session", issued_session.session_token)

    return {
        "engine": engine,
        "client": client,
        "csrf_token": issued_session.csrf_token,
        "session_token": issued_session.session_token,
        "user_owner": user_owner,
        "user_other": user_other,
        "org_a": org_a,
        "org_b": org_b,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "exp": exp,
    }


# ==============================================================================
# 1. CANDIDATE SELECTION & PROVENANCE TESTS
# ==============================================================================


def test_candidate_validation_completed_vs_failed(m9_env):
    """Test that completed trials are validated as eligible while failed trials are flagged."""
    client = m9_env["client"]
    ws_id = m9_env["ws_a"].id
    exp_id = m9_env["exp"].id

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/recommendations/validate-candidates",
        json={"experiment_ids": [exp_id]},
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4

    # Trials 1, 2, 3 should be eligible
    eligible_items = [d for d in data if d["is_eligible"]]
    assert len(eligible_items) == 3

    # Trial 4 is failed
    failed_item = next(d for d in data if d["trial_id"] == "trial-failed-4")
    assert not failed_item["is_eligible"]
    assert any("must be COMPLETED" in r for r in failed_item["exclusion_reasons"])


# ==============================================================================
# 2. COMPARABILITY TESTS
# ==============================================================================


def test_comparability_verification_identical_cohort():
    """Verify that candidates evaluated on identical datasets, suites, and splits are marked comparable."""
    candidates = [
        {
            "id": "c1",
            "dataset_version_id": "ds-v-1",
            "evaluation_suite_version_id": "suite-v-1",
            "evaluation_split": "VALIDATION",
            "rubric_version": 1,
        },
        {
            "id": "c2",
            "dataset_version_id": "ds-v-1",
            "evaluation_suite_version_id": "suite-v-1",
            "evaluation_split": "VALIDATION",
            "rubric_version": 1,
        },
    ]
    res = ComparabilityService.verify_cohort_comparability(candidates)
    assert res.is_cohort_comparable is True
    assert len(res.discrepancies) == 0
    assert res.candidate_statuses["c1"] == CandidateProvenanceStatus.VERIFIED
    assert res.candidate_statuses["c2"] == CandidateProvenanceStatus.VERIFIED


def test_comparability_verification_split_and_suite_mismatch():
    """Verify that differing evaluation splits or suite versions are strictly caught as INCOMPATIBLE."""
    candidates = [
        {
            "id": "c1",
            "dataset_version_id": "ds-v-1",
            "evaluation_suite_version_id": "suite-v-1",
            "evaluation_split": "VALIDATION",
        },
        {
            "id": "c2",
            "dataset_version_id": "ds-v-1",
            "evaluation_suite_version_id": "suite-v-2",  # Different suite!
            "evaluation_split": "DEVELOPMENT",          # Different split!
        },
    ]
    res = ComparabilityService.verify_cohort_comparability(candidates)
    assert res.is_cohort_comparable is False
    assert len(res.discrepancies) == 2
    assert res.candidate_statuses["c2"] == CandidateProvenanceStatus.INCOMPATIBLE


# ==============================================================================
# 3. HARD CONSTRAINT ENGINE TESTS
# ==============================================================================


def test_hard_constraints_filtering():
    """Verify that candidates violating min quality or max latency are marked INELIGIBLE."""
    cand_data = {
        "id": "cand-test",
        "trial_status": "COMPLETED",
        "gate1_approval_id": "gate1-appr-1",
        "hardware_profile_key": "LOCAL_CPU_I5_8GB",
        "aggregate_score": 68.0,  # Below threshold
        "latency_p95_ms": 3200.0, # Above threshold
        "required_ram_mb": 4000.0,
        "estimated_cost_usd": 0.0,
    }

    constraints = {
        "min_quality_score": 75.0,
        "max_p95_latency_ms": 2500.0,
        "max_ram_mb": 8000.0,
    }

    res = ConstraintEngine.evaluate_candidate(cand_data, constraints)
    assert res.is_eligible is False
    assert res.eligibility_status == CandidateEligibilityStatus.INELIGIBLE
    assert len(res.exclusion_reasons) == 2
    assert any("below minimum required threshold of 75.0" in r for r in res.exclusion_reasons)
    assert any("exceeds configured maximum threshold of 2500.0 ms" in r for r in res.exclusion_reasons)


def test_hard_constraint_missing_cost_cannot_assume_below_budget():
    """Strict Invariant: Missing or unknown pricing CANNOT be assumed within budget."""
    cand_data = {
        "id": "cand-cloud",
        "trial_status": "COMPLETED",
        "gate1_approval_id": "gate1-appr-1",
        "hardware_profile_key": "LOCAL_CPU_I5_8GB",
        "aggregate_score": 90.0,
        "latency_p95_ms": 500.0,
        "estimated_cost_usd": "UNKNOWN",  # Missing price!
    }

    constraints = {
        "max_budget_usd": 5.00,
    }

    res = ConstraintEngine.evaluate_candidate(cand_data, constraints)
    assert res.is_eligible is False
    assert res.eligibility_status == CandidateEligibilityStatus.INSUFFICIENT_EVIDENCE
    assert any("Cost is unknown/unavailable" in r for r in res.exclusion_reasons)


# ==============================================================================
# 4. OBJECTIVE REGISTRY TESTS
# ==============================================================================


def test_objective_registry_queries():
    """Test registry queries, optimization directions, and key validations."""
    obj = ObjectiveRegistry.get_objective("aggregate_score")
    assert obj is not None
    assert obj.direction == OptimizationDirection.MAXIMIZE
    assert obj.unit == "pts"

    lat = ObjectiveRegistry.get_objective("latency_p95_ms")
    assert lat is not None
    assert lat.direction == OptimizationDirection.MINIMIZE
    assert lat.unit == "ms"

    # Validation
    invalid_keys = ObjectiveRegistry.validate_keys(["aggregate_score", "fake_metric"])
    assert invalid_keys == ["fake_metric"]


# ==============================================================================
# 5. NORMALIZATION TESTS
# ==============================================================================


def test_normalization_directions_and_constant_handling():
    """Test min-max normalization with direction awareness and zero-variance protection."""
    candidates = [
        {"aggregate_score": 70.0, "latency_p95_ms": 1000.0, "constant_metric": 5.0},
        {"aggregate_score": 90.0, "latency_p95_ms": 500.0, "constant_metric": 5.0},
    ]

    objectives = ["aggregate_score", "latency_p95_ms"]
    norm_cands, snapshot = NormalizationService.normalize_candidates(candidates, objectives)

    # For aggregate_score (MAXIMIZE): 70 -> 0.0 (worst), 90 -> 1.0 (best)
    assert norm_cands[0]["aggregate_score"] == 0.0
    assert norm_cands[1]["aggregate_score"] == 1.0

    # For latency_p95_ms (MINIMIZE): 1000 -> 0.0 (worst), 500 -> 1.0 (best)
    assert norm_cands[0]["latency_p95_ms"] == 0.0
    assert norm_cands[1]["latency_p95_ms"] == 1.0

    # Test constant metric protection (min == max)
    const_candidates = [
        {"aggregate_score": 85.0},
        {"aggregate_score": 85.0},
    ]
    norm_cands_const, _ = NormalizationService.normalize_candidates(const_candidates, ["aggregate_score"])
    assert norm_cands_const[0]["aggregate_score"] == 1.0
    assert norm_cands_const[1]["aggregate_score"] == 1.0


# ==============================================================================
# 6. PARETO DOMINANCE TESTS
# ==============================================================================


def test_pareto_dominance_cases():
    """Test mathematically known Pareto dominance cases:
    - Candidate A strictly dominates Candidate B
    - Candidate A and Candidate C are incomparable trade-offs (both on frontier)
    - Ineligible candidate excluded from frontier
    """
    candidates = [
        # Candidate 1: High Quality (1.0), High Latency (0.4)
        {
            "id": "c1",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 1.0, "latency_p95_ms": 0.4},
        },
        # Candidate 2: Moderate Quality (0.6), Ultra-fast Latency (1.0)
        {
            "id": "c2",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 0.6, "latency_p95_ms": 1.0},
        },
        # Candidate 3: Strictly Dominated by C1 (Lower quality 0.5 < 1.0, and worse latency 0.3 < 0.4)
        {
            "id": "c3",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 0.5, "latency_p95_ms": 0.3},
        },
        # Candidate 4: Ineligible Candidate (Failed hard constraint)
        {
            "id": "c4",
            "is_eligible": False,
            "normalized_objective_values": {"aggregate_score": 1.0, "latency_p95_ms": 1.0},
        },
    ]

    objectives = ["aggregate_score", "latency_p95_ms"]
    res = ParetoEngine.compute_frontier(candidates, objectives)

    # Frontier should contain only c1 and c2
    assert "c1" in res.frontier_candidate_ids
    assert "c2" in res.frontier_candidate_ids
    assert "c3" not in res.frontier_candidate_ids
    assert "c4" not in res.frontier_candidate_ids
    assert len(res.frontier_candidate_ids) == 2

    # Dominance verification
    assert "c3" in res.dominates["c1"]
    assert "c1" in res.dominated_by["c3"]
    assert len(res.dominated_by["c1"]) == 0
    assert len(res.dominated_by["c2"]) == 0


def test_pareto_missing_data_conservative_default():
    """Strict Invariant: Dominance cannot be declared when objective data is missing."""
    vec_a = {"aggregate_score": 0.9, "latency_p95_ms": 0.8}
    vec_b = {"aggregate_score": 0.7, "latency_p95_ms": None}  # Missing latency!

    objectives = ["aggregate_score", "latency_p95_ms"]

    # Neither can be declared dominating the other
    assert ParetoEngine.check_dominance(vec_a, vec_b, objectives) is False
    assert ParetoEngine.check_dominance(vec_b, vec_a, objectives) is False


# ==============================================================================
# 7. WEIGHTED SCORING TESTS
# ==============================================================================


def test_weighted_scoring_validation_and_ranking():
    """Verify weight sum validation, preset calculations, and deterministic ranking."""
    # 1. Invalid weight validations
    assert len(WeightedScoringEngine.validate_weights({"aggregate_score": 0.8})) > 0  # Sum != 1.0
    assert len(WeightedScoringEngine.validate_weights({"aggregate_score": -0.2, "latency_p95_ms": 1.2})) > 0  # Negative
    assert len(WeightedScoringEngine.validate_weights({"unknown_metric": 1.0})) > 0  # Unknown

    # 2. Valid calculation under Quality-First preset
    candidates = [
        {
            "id": "c1",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 1.0, "latency_p95_ms": 0.5, "required_ram_mb": 0.5},
        },
        {
            "id": "c2",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 0.6, "latency_p95_ms": 1.0, "required_ram_mb": 0.8},
        },
    ]

    weights = PREFERENCE_PRESETS["QUALITY_FIRST"]  # 0.60 Quality, 0.20 Latency, 0.20 RAM
    res = WeightedScoringEngine.calculate_weighted_scores(candidates, weights, scenario_name="Quality First")

    # Score c1 = 0.6*1.0 + 0.2*0.5 + 0.2*0.5 = 0.80
    # Score c2 = 0.6*0.6 + 0.2*1.0 + 0.2*0.8 = 0.36 + 0.20 + 0.16 = 0.72
    cand1 = next(d for d in res.ranked_candidates if d.candidate_id == "c1")
    cand2 = next(d for d in res.ranked_candidates if d.candidate_id == "c2")

    assert cand1.weighted_score == 0.80
    assert cand1.rank == 1
    assert cand2.weighted_score == 0.72
    assert cand2.rank == 2


# ==============================================================================
# 8. SENSITIVITY ANALYSIS TESTS
# ==============================================================================


def test_sensitivity_analysis_rank_shift():
    """Verify that sensitivity analysis detects ranking shifts across weight distributions."""
    candidates = [
        {
            "id": "c_qual",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 1.0, "latency_p95_ms": 0.1},
        },
        {
            "id": "c_speed",
            "is_eligible": True,
            "normalized_objective_values": {"aggregate_score": 0.1, "latency_p95_ms": 1.0},
        },
    ]

    base_weights = {"aggregate_score": 0.50, "latency_p95_ms": 0.50}
    frontier_ids = ["c_qual", "c_speed"]

    report = SensitivityAnalysisEngine.analyze_sensitivity(
        candidates, base_weights, frontier_ids
    )

    assert len(report.candidate_summaries) == 2
    assert report.pareto_frontier_independent is True
    assert "statistical confidence intervals" in report.disclaimer


# ==============================================================================
# 9. EXPLANATION ENGINE TESTS
# ==============================================================================


def test_explanation_engine_outputs():
    """Verify deterministic explanations for frontier, dominated, and ineligible candidates."""
    # 1. Frontier member
    expl_frontier = ExplanationEngine.explain_candidate(
        candidate_id="c1",
        label="Qwen 1.5B Q4",
        eligibility_status=CandidateEligibilityStatus.ELIGIBLE,
        exclusion_reasons=[],
        is_frontier_member=True,
        dominating_ids=[],
        dominated_ids=["c3"],
        raw_values={"aggregate_score": 92.5, "latency_p95_ms": 850.0},
        evidence_summary={"aggregate_score": "MEASURED", "latency_p95_ms": "MEASURED"},
    )
    assert "non-dominated Pareto frontier member" in expl_frontier
    assert "strictly dominates 1 other candidate(s)" in expl_frontier

    # 2. Dominated candidate
    expl_dominated = ExplanationEngine.explain_candidate(
        candidate_id="c3",
        label="Qwen 0.5B FP16",
        eligibility_status=CandidateEligibilityStatus.ELIGIBLE,
        exclusion_reasons=[],
        is_frontier_member=False,
        dominating_ids=["c1"],
        dominated_ids=[],
        raw_values={"aggregate_score": 78.0},
        evidence_summary={},
        all_candidates_map={"c1": {"candidate_label": "Qwen 1.5B Q4"}},
    )
    assert "not on the Pareto frontier" in expl_dominated
    assert "strictly dominated by other eligible" in expl_dominated
    assert "'Qwen 1.5B Q4'" in expl_dominated

    # 3. Ineligible candidate
    expl_inelig = ExplanationEngine.explain_candidate(
        candidate_id="c4",
        label="Failed Candidate",
        eligibility_status=CandidateEligibilityStatus.INELIGIBLE,
        exclusion_reasons=["P95 latency exceeds maximum threshold."],
        is_frontier_member=False,
        dominating_ids=[],
        dominated_ids=[],
        raw_values={},
        evidence_summary={},
    )
    assert "classified as INELIGIBLE" in expl_inelig
    assert "Hard constraint failure reasons" in expl_inelig


# ==============================================================================
# 10. REPRODUCIBILITY & CANONICAL DIGEST TESTS
# ==============================================================================


def test_canonical_digest_determinism():
    """Verify that equivalent JSON payloads with different key orders produce identical SHA-256 digests."""
    data_1 = {"alpha": 1, "beta": "value", "gamma": [1, 2, 3]}
    data_2 = {"gamma": [1, 2, 3], "beta": "value", "alpha": 1}

    digest_1 = compute_canonical_digest(data_1)
    digest_2 = compute_canonical_digest(data_2)

    assert digest_1 == digest_2
    assert len(digest_1) == 64


# ==============================================================================
# 11. API INTEGRATION TESTS
# ==============================================================================


def test_api_recommendation_run_lifecycle_and_decision(m9_env):
    """End-to-end API test: create/execute run, inspect matrix/frontier, record decision, and export reports."""
    client = m9_env["client"]
    ws_id = m9_env["ws_a"].id
    exp_id = m9_env["exp"].id

    # 1. List supported objectives
    res_obj = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/objectives")
    assert res_obj.status_code == 200
    objectives = res_obj.json()
    assert len(objectives) >= 5

    # 2. Create and execute recommendation run
    payload = {
        "name": "Q4 Model Comparison Run",
        "description": "Multi-objective trade-off analysis across Qwen trials",
        "experiment_ids": [exp_id],
        "selected_objectives": ["aggregate_score", "latency_p95_ms", "required_ram_mb"],
        "weights": {"aggregate_score": 0.50, "latency_p95_ms": 0.30, "required_ram_mb": 0.20},
        "hard_constraints": {
            "min_quality_score": 80.0,
            "max_p95_latency_ms": 2000.0,
        },
    }

    res_create = client.post(
        f"/api/v1/workspaces/{ws_id}/recommendations/runs",
        json=payload,
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_create.status_code == 201
    run_data = res_create.json()

    run_id = run_data["id"]
    assert run_data["name"] == "Q4 Model Comparison Run"
    assert run_data["status"] in (RecommendationRunStatus.COMPLETED.value, RecommendationRunStatus.COMPLETED_WITH_WARNINGS.value)
    assert run_data["total_candidates"] == 4
    # Trials 1 & 2 passed quality >= 80; Trial 3 had 78.0 (failed); Trial 4 was failed trial (failed)
    assert run_data["eligible_candidates"] == 2
    assert run_data["frontier_candidates"] == 2  # Both T1 and T2 are on the Pareto frontier

    # 3. Get recommendation run details
    res_get = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert len(detail["candidates"]) == 4

    # 4. Record human review decision
    cand_frontier = next(c for c in detail["candidates"] if c["pareto_frontier_member"])
    decision_payload = {
        "selected_candidate_id": cand_frontier["id"],
        "decision": RecommendationDecisionType.ACCEPTED_FOR_FURTHER_REVIEW.value,
        "decision_reason": "High quality score (92.5) with acceptable tail latency within local budget.",
    }
    res_dec = client.post(
        f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}/decide",
        json=decision_payload,
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_dec.status_code == 201
    dec_data = res_dec.json()
    assert dec_data["decision"] == RecommendationDecisionType.ACCEPTED_FOR_FURTHER_REVIEW.value

    # 5. Export Reports (JSON, Markdown, CSV)
    res_json = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}/export?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]

    res_md = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}/export?format=markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "MIZAN Recommendation Report" in res_md.text

    res_csv = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "candidate_label" in res_csv.text

    # 6. Verify Scenarios in serialized run response
    res_detail = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "scenarios" in detail_data
    assert len(detail_data["scenarios"]) >= 1
    assert detail_data["scenarios"][0]["scenario_name"] == "User Preference"

    # 7. Test Presets Endpoint
    res_presets = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/presets")
    assert res_presets.status_code == 200
    presets_data = res_presets.json()
    assert "QUALITY_FIRST" in presets_data
    assert "BALANCED" in presets_data

    # 8. Archive Run
    res_archive = client.post(
        f"/api/v1/workspaces/{ws_id}/recommendations/runs/{run_id}/archive",
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_archive.status_code == 200
    assert res_archive.json()["status"] == RecommendationRunStatus.ARCHIVED.value


def test_api_optimization_profiles_crud(m9_env):
    """Test full CRUD operations for Optimization Profiles."""
    client = m9_env["client"]
    ws_id = m9_env["ws_a"].id

    # Create
    req = {
        "name": "Standard Production Profile",
        "description": "Standard SLA targets for inference",
        "objectives": ["aggregate_score", "latency_p95_ms"],
        "weights": {"aggregate_score": 0.70, "latency_p95_ms": 0.30},
        "constraints": {"min_quality_score": 85.0},
        "preferred_hardware_profile": "LOCAL_CPU_I5_8GB",
    }
    res_create = client.post(
        f"/api/v1/workspaces/{ws_id}/recommendations/profiles",
        json=req,
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_create.status_code == 201
    prof = res_create.json()
    prof_id = prof["id"]
    assert prof["name"] == "Standard Production Profile"
    assert prof["version"] == 1

    # List
    res_list = client.get(f"/api/v1/workspaces/{ws_id}/recommendations/profiles")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # Update
    res_update = client.put(
        f"/api/v1/workspaces/{ws_id}/recommendations/profiles/{prof_id}",
        json={"name": "Updated Profile Name"},
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Updated Profile Name"
    assert res_update.json()["version"] == 2

    # Delete
    res_del = client.delete(
        f"/api/v1/workspaces/{ws_id}/recommendations/profiles/{prof_id}",
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_del.status_code == 204


# ==============================================================================
# 12. TENANT ISOLATION & SECURITY TESTS
# ==============================================================================


def test_tenant_isolation_anti_enumeration(m9_env):
    """Test that User in Workspace B cannot access or enumerate Workspace A recommendation runs."""
    client = m9_env["client"]
    ws_a_id = m9_env["ws_a"].id
    ws_b_id = m9_env["ws_b"].id
    exp_id = m9_env["exp"].id

    # Create run in Workspace A
    res_run = client.post(
        f"/api/v1/workspaces/{ws_a_id}/recommendations/runs",
        json={
            "name": "Secret Run A",
            "experiment_ids": [exp_id],
        },
        headers={"X-CSRF-Token": m9_env["csrf_token"]},
    )
    assert res_run.status_code == 201
    run_a_id = res_run.json()["id"]

    # Switch session to user_other (member of Workspace B only)
    with Session(m9_env["engine"]) as db:
        session_other = session_service.create_session(
            db, user_id=m9_env["user_other"].id
        )
        db.commit()
    client.cookies.set("mizan_session", session_other.session_token)

    # Attempt to read run_a from Workspace B endpoint (returns 404 anti-enumeration)
    res_cross = client.get(f"/api/v1/workspaces/{ws_b_id}/recommendations/runs/{run_a_id}")
    assert res_cross.status_code == 404
