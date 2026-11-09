"""Comprehensive Unit & Integration Test Suite for Milestone 7: Experiment Orchestration & Trial Matrix Engine."""

from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.dataset import DatasetVersionStatus
from app.models.evaluation import SplitType
from app.models.experiment import Experiment, ExperimentStatus, TrialStatus
from app.models.identity import AccountStatus, User
from app.modules.auth.services import password_service, session_service
from app.modules.datasets.services import dataset_service
from app.modules.experiments.digest import compute_canonical_config_digest
from app.modules.experiments.matrix.generator import TrialMatrixGenerator
from app.modules.experiments.matrix.presets import get_preset_configs
from app.modules.experiments.matrix.validator import validate_trial_matrix
from app.modules.experiments.repositories.experiment_repository import ExperimentRepository
from app.modules.experiments.schemas.experiment import (
    ExperimentCreate,
    MatrixGenerateStrategy,
)
from app.modules.experiments.schemas.trial import TrialConfig
from app.modules.experiments.services.execution_service import ExperimentExecutionService
from app.modules.experiments.services.state_machine import ExperimentStateMachine
from app.modules.rag.embeddings.mock_provider import MockEmbeddingProvider
from app.modules.rag.providers.mock_provider import MockLLMProvider
from app.modules.rag.vector_store.base import VectorStoreProvider
from app.modules.storage import (
    LocalStorageProvider,
    set_storage_provider_override,
)
from app.modules.workspaces.services import organization_service, workspace_service


class InMemoryVectorStore(VectorStoreProvider):
    def __init__(self):
        self.collections: dict[str, list] = {}

    def create_collection(self, collection_name: str, dimension: int) -> None:
        if collection_name not in self.collections:
            self.collections[collection_name] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def upsert_chunks(self, collection_name: str, records: list) -> None:
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        self.collections[collection_name].extend(records)

    def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        workspace_id: str,
        dataset_version_id: str | None = None,
        top_k: int = 4,
        score_threshold: float = 0.0,
    ) -> list:
        from app.modules.rag.vector_store.base import ScoredChunk
        return [
            ScoredChunk(
                id=f"chunk-{i}",
                document_id="doc-1",
                chunk_index=i,
                score=0.95 - (i * 0.05),
                text="Financial records must be retained for 7 years.",
                payload={"document_name": "procedure.txt"},
            )
            for i in range(min(top_k, 3))
        ]

    def delete_collection(self, collection_name: str) -> None:
        self.collections.pop(collection_name, None)

    def count_vectors(self, collection_name: str, workspace_id: str) -> int:
        return len(self.collections.get(collection_name, []))

    def close(self) -> None:
        pass


# ===========================================================================
# UNIT TESTS: DIGEST, CONFIG VALIDATION, SPLIT PROTECTION, PRESETS
# ===========================================================================


def test_canonical_digest_determinism():
    """Verify recursive key-sorted hashing produces deterministic digests."""
    cfg1 = {"chunk_size": 500, "overlap": 100, "provider": "mock", "nested": {"b": 2, "a": 1}}
    cfg2 = {"overlap": 100, "nested": {"a": 1, "b": 2}, "provider": "mock", "chunk_size": 500}
    cfg3 = {"chunk_size": 501, "overlap": 100, "provider": "mock", "nested": {"b": 2, "a": 1}}

    h1 = compute_canonical_config_digest(cfg1)
    h2 = compute_canonical_config_digest(cfg2)
    h3 = compute_canonical_config_digest(cfg3)

    assert h1 == h2, "Different key ordering must yield identical canonical digests"
    assert h1 != h3, "Different configuration values must produce distinct digests"
    assert len(h1) == 64


def test_trial_config_free_only_policy_and_bounds():
    """Verify free-only provider policy and numeric range bounds."""
    # Permitted free providers
    c1 = TrialConfig(provider_name="mock")
    assert c1.provider_name == "mock"
    c2 = TrialConfig(provider_name="ollama")
    assert c2.provider_name == "ollama"
    c3 = TrialConfig(provider_name="gemini_free")
    assert c3.provider_name == "gemini_free"

    # Paid providers must be rejected
    with pytest.raises(ValueError, match="not supported under Free-Only policy"):
        TrialConfig(provider_name="openai")

    with pytest.raises(ValueError, match="not supported under Free-Only policy"):
        TrialConfig(provider_name="anthropic")

    # Overlap must be strictly less than chunk_size
    with pytest.raises(ValueError, match="must be less than chunk_size_chars"):
        TrialConfig(chunk_size_chars=200, chunk_overlap_chars=200)

    # Chunk size bounds
    with pytest.raises(ValueError):
        TrialConfig(chunk_size_chars=40)  # ge=50

    with pytest.raises(ValueError):
        TrialConfig(chunk_size_chars=6000)  # le=5000

    # Top-k bounds
    with pytest.raises(ValueError):
        TrialConfig(top_k=0)  # ge=1

    with pytest.raises(ValueError):
        TrialConfig(top_k=25)  # le=20


def test_holdout_split_protection_invariant():
    """Verify holdout split is reserved strictly and rejected from ordinary experiment tuning."""
    with pytest.raises(ValueError, match="reserved strictly"):
        ExperimentCreate(
            name="Holdout Leak Experiment",
            dataset_id="ds-1",
            dataset_version_id="ver-1",
            evaluation_suite_id="suite-1",
            evaluation_suite_version_id="sver-1",
            evaluation_split=SplitType.HOLDOUT,
        )


def test_preset_matrices_and_matrix_validator():
    """Verify preset configurations produce 3-9 bounded unique trials."""
    baseline = TrialConfig().model_dump()

    for preset_name in ["chunk_sensitivity", "retrieval_depth", "prompt_strategy"]:
        configs = get_preset_configs(preset_name, baseline)
        assert len(configs) == 3
        validate_trial_matrix(configs)

    configs_9 = get_preset_configs("chunk_and_retrieval", baseline)
    assert len(configs_9) == 9
    validate_trial_matrix(configs_9)

    # Under-bounded matrix (<3)
    with pytest.raises(ValueError, match="at least 3 unique trials"):
        validate_trial_matrix(configs[:2])

    # Duplicate configs in matrix
    dup_configs = [configs[0], configs[0], configs[1]]
    with pytest.raises(ValueError, match="Duplicate configuration detected"):
        validate_trial_matrix(dup_configs)


def test_matrix_generator_parametric_variation():
    """Verify Cartesian product generator respects 3-9 bounds."""
    generator = TrialMatrixGenerator()
    baseline = TrialConfig().model_dump()

    # 2 x 2 = 4 trials
    variations = {
        "chunk_size_chars": [300, 700],
        "top_k": [3, 6],
    }
    configs = generator.generate(
        strategy=MatrixGenerateStrategy.PARAMETRIC_VARIATION.value,
        baseline_config=baseline,
        variations=variations,
    )
    assert len(configs) == 4
    validate_trial_matrix(configs)

    # Over 9 variations clamped to 9
    large_vars = {
        "chunk_size_chars": [200, 400, 600, 800],
        "top_k": [2, 4, 6, 8],
    }  # 16 combinations
    configs_clamped = generator.generate(
        strategy=MatrixGenerateStrategy.PARAMETRIC_VARIATION.value,
        baseline_config=baseline,
        variations=large_vars,
    )
    assert len(configs_clamped) == 9
    validate_trial_matrix(configs_clamped)


# ===========================================================================
# INTEGRATION FIXTURES & LIFECYCLE TESTS
# ===========================================================================


@pytest.fixture
def exp_test_env():
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

    tmp_dir = tempfile.TemporaryDirectory()
    storage = LocalStorageProvider(tmp_dir.name)
    set_storage_provider_override(storage)

    client = TestClient(app)
    db = Session(engine, expire_on_commit=False)

    owner = User(
        full_name="Fatima Lead",
        email="fatima@mizan.ae",
        normalized_email="fatima@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(owner)
    db.commit()

    owner_sess = session_service.create_session(db, owner.id)
    org, _ = organization_service.create_organization(db, owner.id, "Mizan Corp", "mizan-corp")
    ws, _ = workspace_service.create_workspace(db, org.id, owner.id, "AI Lab", "ai-lab")

    # Member in other org for tenant isolation
    other_user = User(
        full_name="Other User",
        email="other@mizan.ae",
        normalized_email="other@mizan.ae",
        password_hash=password_service.hash_password("Password123!"),
        status=AccountStatus.ACTIVE,
    )
    db.add(other_user)
    db.commit()
    other_sess = session_service.create_session(db, other_user.id)
    other_org, _ = organization_service.create_organization(db, other_user.id, "Other Org", "other-org")
    other_ws, _ = workspace_service.create_workspace(db, other_org.id, other_user.id, "Other Lab", "other-lab")

    # Setup an approved dataset version & masked document
    ds_resp = client.post(
        f"/api/v1/workspaces/{ws.id}/datasets",
        json={"name": "Approved Knowledge", "slug": "appr-know"},
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )
    dataset_id = ds_resp.json()["dataset"]["id"]
    version_id = ds_resp.json()["version"]["id"]

    sample_text = (
        "Enterprise Procedure:\n"
        "Contact: Fatima Al-Zaabi\n"
        "Emirates ID: 784-1980-1234567-1\n"
        "Policy: Financial records must be retained for 7 years."
    )
    client.post(
        f"/api/v1/workspaces/{ws.id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
        files={"file": ("procedure.txt", sample_text.encode("utf-8"), "text/plain")},
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )

    ver = db.query(dataset_service.DatasetVersion).filter_by(id=version_id).first()
    ver.status = DatasetVersionStatus.READY
    ver.content_hash = "mockhash123"
    db.commit()

    # Masking run & Gate 1 approval
    run_resp = client.post(
        f"/api/v1/workspaces/{ws.id}/masking-runs",
        json={"dataset_id": dataset_id, "dataset_version_id": version_id},
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )
    run_id = run_resp.json()["id"]

    client.post(
        f"/api/v1/workspaces/{ws.id}/masking-runs/{run_id}/gate1/approve",
        json={"decision_reason": "Verified and approved for AI testing."},
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )

    # Setup frozen evaluation suite
    suite_resp = client.post(
        f"/api/v1/workspaces/{ws.id}/evaluation/suites",
        json={
            "name": "QA Exam Suite",
            "slug": "qa-exam-suite",
            "dataset_id": dataset_id,
            "source_dataset_version_id": version_id,
        },
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )
    suite_id = suite_resp.json()["id"]

    # Add 2 manual evaluation cases
    client.post(
        f"/api/v1/workspaces/{ws.id}/evaluation/suites/{suite_id}/cases",
        json={
            "question": "How long must financial records be retained?",
            "expected_answer": "Financial records must be retained for 7 years.",
            "category": "FACTUAL",
            "difficulty": "EASY",
            "split": "VALIDATION",
        },
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )
    client.post(
        f"/api/v1/workspaces/{ws.id}/evaluation/suites/{suite_id}/cases",
        json={
            "question": "What is the contact information for Enterprise Procedure?",
            "expected_answer": "Fatima Al-Zaabi",
            "category": "FACTUAL",
            "difficulty": "MEDIUM",
            "split": "VALIDATION",
        },
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )

    # Finalize suite to create frozen version
    finalize_resp = client.post(
        f"/api/v1/workspaces/{ws.id}/evaluation/suites/{suite_id}/finalize",
        json={},
        cookies={"mizan_session": owner_sess.session_token},
        headers={"X-CSRF-Token": owner_sess.csrf_token},
    )
    suite_ver_id = finalize_resp.json()["id"]

    yield {
        "client": client,
        "engine": engine,
        "db": db,
        "owner": owner,
        "ws_id": ws.id,
        "dataset_id": dataset_id,
        "version_id": version_id,
        "suite_id": suite_id,
        "suite_ver_id": suite_ver_id,
        "storage": storage,
        "owner_cookies": {"mizan_session": owner_sess.session_token},
        "owner_headers": {"X-CSRF-Token": owner_sess.csrf_token},
        "other_ws_id": other_ws.id,
        "other_cookies": {"mizan_session": other_sess.session_token},
        "other_headers": {"X-CSRF-Token": other_sess.csrf_token},
    }

    set_storage_provider_override(None)
    tmp_dir.cleanup()


def test_state_machine_valid_and_invalid_transitions(exp_test_env):
    """Verify experiment and trial state machine transitions and audit events."""
    db = exp_test_env["db"]
    ws_id = exp_test_env["ws_id"]
    owner = exp_test_env["owner"]
    ws = workspace_service.get_workspace(db, ws_id)
    repo = ExperimentRepository()
    sm = ExperimentStateMachine(repo)

    exp = Experiment(
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        name="State Machine Test",
        slug="sm-test",
        status=ExperimentStatus.DRAFT,
        dataset_id=exp_test_env["dataset_id"],
        dataset_version_id=exp_test_env["version_id"],
        evaluation_suite_id=exp_test_env["suite_id"],
        evaluation_suite_version_id=exp_test_env["suite_ver_id"],
        evaluation_split=SplitType.VALIDATION,
        created_by=owner.id,
    )
    repo.create_experiment(db, exp)

    # Valid transitions: DRAFT -> VALIDATING -> READY -> RUNNING -> COMPLETED
    sm.transition_experiment(db, exp, ExperimentStatus.VALIDATING, actor_id=owner.id)
    assert exp.status == ExperimentStatus.VALIDATING

    sm.transition_experiment(db, exp, ExperimentStatus.READY, actor_id=owner.id)
    assert exp.status == ExperimentStatus.READY

    sm.transition_experiment(db, exp, ExperimentStatus.RUNNING, actor_id=owner.id)
    assert exp.status == ExperimentStatus.RUNNING

    sm.transition_experiment(db, exp, ExperimentStatus.COMPLETED, actor_id=owner.id)
    assert exp.status == ExperimentStatus.COMPLETED

    # Invalid transition from COMPLETED (terminal) raises ValueError
    with pytest.raises(ValueError, match="Invalid experiment state transition"):
        sm.transition_experiment(db, exp, ExperimentStatus.RUNNING, actor_id=owner.id)

    # Audit events verified
    events = repo.list_events(db, exp.id)
    assert len(events) == 4


def test_experiments_api_full_lifecycle(exp_test_env):
    """Verify End-to-End Experiment Creation, Matrix Generation, Validation, Execution, and Comparison."""
    client = exp_test_env["client"]
    ws_id = exp_test_env["ws_id"]
    dataset_id = exp_test_env["dataset_id"]
    version_id = exp_test_env["version_id"]
    suite_id = exp_test_env["suite_id"]
    suite_ver_id = exp_test_env["suite_ver_id"]
    cookies = exp_test_env["owner_cookies"]
    headers = exp_test_env["owner_headers"]
    db = exp_test_env["db"]

    # 1. Create Experiment
    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/experiments",
        json={
            "name": "Chunk Size Sensitivity Study",
            "slug": "chunk-study",
            "description": "Evaluate chunk size impacts on groundedness and latency.",
            "dataset_id": dataset_id,
            "dataset_version_id": version_id,
            "evaluation_suite_id": suite_id,
            "evaluation_suite_version_id": suite_ver_id,
            "evaluation_split": "VALIDATION",
            "baseline_config": {
                "chunk_size_chars": 500,
                "chunk_overlap_chars": 100,
                "top_k": 4,
                "provider_name": "mock",
                "model_name": "mock-rag-v1",
            },
        },
        cookies=cookies,
        headers=headers,
    )
    assert create_resp.status_code == 201
    exp_data = create_resp.json()
    exp_id = exp_data["id"]
    assert exp_data["status"] == "DRAFT"
    assert exp_data["dataset_id"] == dataset_id
    assert exp_data["evaluation_suite_id"] == suite_id
    assert exp_data["gate1_approval_id"] is not None

    # 2. Generate 3-Trial Preset Matrix
    matrix_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/matrix",
        json={
            "strategy": "PRESET_MATRIX",
            "preset_name": "chunk_sensitivity",
        },
        cookies=cookies,
        headers=headers,
    )
    assert matrix_resp.status_code == 200
    m_data = matrix_resp.json()
    assert m_data["status"] == "READY"
    assert m_data["total_trials"] == 3
    assert len(m_data["trials"]) == 3
    assert m_data["trials"][0]["status"] == "PENDING"

    # 3. Validate Matrix Endpoint
    val_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/validate",
        cookies=cookies,
        headers=headers,
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is True
    assert val_resp.json()["total_trials"] == 3

    # 4. Execute Experiment using ExecutionService directly with mock vector store & LLM
    v_store = InMemoryVectorStore()
    embedder = MockEmbeddingProvider()
    llm = MockLLMProvider()

    exec_service = ExperimentExecutionService(
        storage=exp_test_env["storage"],
        vector_store=v_store,
        embedding_provider=embedder,
    )

    completed_exp = exec_service.execute_experiment(
        db=db,
        workspace_id=ws_id,
        experiment_id=exp_id,
        actor_id=exp_test_env["owner"].id,
        llm_provider_override=llm,
    )
    assert completed_exp.status == ExperimentStatus.COMPLETED
    assert completed_exp.completed_trials == 3
    assert completed_exp.failed_trials == 0

    repo = ExperimentRepository()
    trials = repo.list_trials(db, exp_id)
    for t in trials:
        assert t.status == TrialStatus.COMPLETED
        assert t.aggregate_score is not None
        assert t.evaluation_run_id is not None
        assert t.latency_p50_ms is not None

    # 5. Retrieve Comparison via API
    comp_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/comparison",
        cookies=cookies,
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["experiment_id"] == exp_id
    assert comp_data["completed_trials"] == 3
    assert len(comp_data["trials"]) == 3
    assert comp_data["compatibility_verified"] is True
    assert len(comp_data["metric_observations"]) > 0

    # Verify factual observation structure (NO M9 optimal/best claims)
    for obs in comp_data["metric_observations"]:
        assert "metric_key" in obs
        assert obs["highest_observed_score"] is not None

    # 6. Export Report via API (JSON, Markdown, CSV)
    json_export = client.get(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/export?format=json",
        cookies=cookies,
    )
    assert json_export.status_code == 200
    assert "experiment_id" in json_export.json()

    md_export = client.get(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/export?format=markdown",
        cookies=cookies,
    )
    assert md_export.status_code == 200
    assert "# Experiment Report:" in md_export.text
    assert "| Trial # |" in md_export.text
    assert "Factual Observations" in md_export.text

    csv_export = client.get(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/export?format=csv",
        cookies=cookies,
    )
    assert csv_export.status_code == 200
    assert "trial_number,trial_name,status" in csv_export.text

    # 7. Tenant Isolation: Other workspace cannot access or mutate
    other_cookies = exp_test_env["other_cookies"]
    other_ws_id = exp_test_env["other_ws_id"]

    other_get = client.get(
        f"/api/v1/workspaces/{other_ws_id}/experiments/{exp_id}",
        cookies=other_cookies,
    )
    assert other_get.status_code == 404

    other_cancel = client.post(
        f"/api/v1/workspaces/{other_ws_id}/experiments/{exp_id}/cancel",
        cookies=other_cookies,
        headers=exp_test_env["other_headers"],
    )
    assert other_cancel.status_code == 404


def test_failure_isolation_and_partial_completion(exp_test_env):
    """Verify that a single trial failure marks trial FAILED and experiment COMPLETED_WITH_ERRORS."""
    db = exp_test_env["db"]
    client = exp_test_env["client"]
    ws_id = exp_test_env["ws_id"]
    dataset_id = exp_test_env["dataset_id"]
    version_id = exp_test_env["version_id"]
    suite_id = exp_test_env["suite_id"]
    suite_ver_id = exp_test_env["suite_ver_id"]
    cookies = exp_test_env["owner_cookies"]
    headers = exp_test_env["owner_headers"]

    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/experiments",
        json={
            "name": "Fault Isolation Experiment",
            "slug": "fault-iso",
            "dataset_id": dataset_id,
            "dataset_version_id": version_id,
            "evaluation_suite_id": suite_id,
            "evaluation_suite_version_id": suite_ver_id,
            "evaluation_split": "VALIDATION",
            "baseline_config": {"provider_name": "mock"},
        },
        cookies=cookies,
        headers=headers,
    )
    exp_id = create_resp.json()["id"]

    client.post(
        f"/api/v1/workspaces/{ws_id}/experiments/{exp_id}/matrix",
        json={"strategy": "PRESET_MATRIX", "preset_name": "chunk_sensitivity"},
        cookies=cookies,
        headers=headers,
    )

    class FailingOnSecondTrialLLM(MockLLMProvider):
        call_count = 0

        def generate(self, *args, **kwargs):
            self.call_count += 1
            if self.call_count > 2:  # Fail on trial 2
                raise RuntimeError("Simulated transient LLM failure during trial 2")
            return super().generate(*args, **kwargs)

    failing_llm = FailingOnSecondTrialLLM()
    exec_service = ExperimentExecutionService(
        storage=exp_test_env["storage"],
        vector_store=InMemoryVectorStore(),
        embedding_provider=MockEmbeddingProvider(),
    )

    completed_exp = exec_service.execute_experiment(
        db=db,
        workspace_id=ws_id,
        experiment_id=exp_id,
        actor_id=exp_test_env["owner"].id,
        llm_provider_override=failing_llm,
    )

    # Verification of failure isolation
    assert completed_exp.status == ExperimentStatus.COMPLETED_WITH_ERRORS
    assert completed_exp.completed_trials > 0
    assert completed_exp.failed_trials > 0

    repo = ExperimentRepository()
    trials = repo.list_trials(db, exp_id)
    failed_t = [t for t in trials if t.status == TrialStatus.FAILED]
    completed_t = [t for t in trials if t.status == TrialStatus.COMPLETED]
    assert len(failed_t) >= 1
    assert len(completed_t) >= 1
    assert "failed" in failed_t[0].error_summary.lower()
