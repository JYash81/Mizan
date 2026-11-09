"""Comprehensive Automated Test Suite for Milestone 10:
Model Building, Fine-Tuning, Quantization & Reproducible Colab Lab.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.dataset import (
    Dataset,
    DatasetStatus,
    DatasetVersion,
    DatasetVersionStatus,
    Document,
    DocumentFileType,
)
from app.models.evaluation import (
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationSuite,
    EvaluationSuiteStatus,
    EvaluationSuiteVersion,
)
from app.models.hardware import (
    EvidenceType,
    HardwareProfile,
    HardwareProfileCategory,
)
from app.models.identity import AccountStatus, User
from app.models.masking import Gate1Approval, Gate1Decision, MaskingRun, MaskingRunStatus
from app.models.model_building import (
    ArtifactType,
    ExecutionMode,
    ExternalProcessingAuthorization,
    LicenseStatus,
    ModelAccessStatus,
    ModelBuildRecipe,
    ModelBuildRun,
    ModelBuildStatus,
    ModelRole,
    ModelSource,
    StagedModelArtifact,
)
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
from app.modules.auth.services import password_service, session_service
from app.modules.model_building.artifact_staging_service import (
    ArtifactStagingError,
    stage_model_artifact,
)
from app.modules.model_building.build_manifest import generate_build_manifest
from app.modules.model_building.build_preflight import run_build_preflight
from app.modules.model_building.build_recipe_registry import (
    sync_build_recipes,
    validate_recipe_compatibility,
)
from app.modules.model_building.checkpoint_service import (
    CheckpointError,
    record_checkpoint,
    validate_resume_compatibility,
)
from app.modules.model_building.dataset_preparation import (
    create_deterministic_train_val_partitions,
    verify_dataset_eligibility,
)
from app.modules.model_building.model_evaluation_service import (
    link_model_evaluation,
)
from app.modules.model_building.model_source_catalog import (
    resolve_model_revision,
    sync_curated_model_catalog,
    validate_license_and_access,
)
from app.modules.model_building.quantization_service import (
    simulate_gguf_conversion_and_quantize,
    validate_awq_quantization_preflight,
    validate_gguf_conversion_preflight,
)


@pytest.fixture
def m10_env():
    """Setup in-memory SQLite database, seeded M10 fixtures, and authenticated TestClient."""
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
        # 1. Seed Reference Hardware Profiles
        hw_local = HardwareProfile(
            profile_key="LOCAL_CPU_I5_8GB",
            name="Local PC (Core i5, 8 GB)",
            category=HardwareProfileCategory.LOCAL_WORKSTATION,
            evidence_type=EvidenceType.MEASURED,
            system_ram_mb=8192,
            supports_cpu_inference=True,
            is_reference=True,
        )
        hw_t4 = HardwareProfile(
            profile_key="NVIDIA_T4_16GB",
            name="NVIDIA T4 (16 GB VRAM)",
            category=HardwareProfileCategory.CLOUD_GPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            system_ram_mb=12800,
            gpu_vram_mb=15360,
            supports_gpu_inference=True,
            supports_fine_tuning=True,
            is_reference=True,
        )
        db.add_all([hw_local, hw_t4])

        # 2. Seed Users
        user_owner = User(
            id="usr-owner-m10",
            email="owner@mizan.org",
            normalized_email="owner@mizan.org",
            full_name="M10 Owner",
            password_hash=password_service.hash_password("SuperSecret123!"),
            status=AccountStatus.ACTIVE,
            email_verified_at=datetime.now(UTC),
        )
        user_other = User(
            id="usr-other-m10",
            email="other@mizan.org",
            normalized_email="other@mizan.org",
            full_name="M10 Other",
            password_hash=password_service.hash_password("SuperSecret123!"),
            status=AccountStatus.ACTIVE,
            email_verified_at=datetime.now(UTC),
        )
        db.add_all([user_owner, user_other])
        db.commit()

        # 3. Seed Organizations and Workspaces
        org_a = Organization(
            id="org-m10-a",
            name="M10 Org A",
            slug="m10-org-a",
            status=OrganizationStatus.ACTIVE,
            created_by=user_owner.id,
        )
        org_b = Organization(
            id="org-m10-b",
            name="M10 Org B",
            slug="m10-org-b",
            status=OrganizationStatus.ACTIVE,
            created_by=user_other.id,
        )
        db.add_all([org_a, org_b])

        ws_a = Workspace(
            id="ws-m10-a",
            organization_id=org_a.id,
            name="Workspace A",
            slug="workspace-m10-a",
            status=WorkspaceStatus.ACTIVE,
            created_by=user_owner.id,
        )
        ws_b = Workspace(
            id="ws-m10-b",
            organization_id=org_b.id,
            name="Workspace B",
            slug="workspace-m10-b",
            status=WorkspaceStatus.ACTIVE,
            created_by=user_other.id,
        )
        db.add_all([ws_a, ws_b])

        db.add(OrganizationMembership(organization_id=org_a.id, user_id=user_owner.id, role=OrganizationRole.OWNER))
        db.add(WorkspaceMembership(workspace_id=ws_a.id, user_id=user_owner.id, role=WorkspaceRole.WORKSPACE_OWNER))
        db.add(OrganizationMembership(organization_id=org_b.id, user_id=user_other.id, role=OrganizationRole.OWNER))
        db.add(WorkspaceMembership(workspace_id=ws_b.id, user_id=user_other.id, role=WorkspaceRole.WORKSPACE_OWNER))
        db.commit()

        # 4. Seed Dataset with Gate 1 Approval
        ds = Dataset(
            id="ds-m10-1",
            workspace_id=ws_a.id,
            name="Approved Customer QA",
            slug="approved-customer-qa",
            status=DatasetStatus.ACTIVE,
            created_by=user_owner.id,
        )
        db.add(ds)
        db.commit()

        ds_v = DatasetVersion(
            id="ds-v-m10-1",
            dataset_id=ds.id,
            version_number=1,
            name="v1",
            content_hash="sha256:dsm10digest",
            status=DatasetVersionStatus.READY,
        )
        db.add(ds_v)
        db.commit()

        mask_run = MaskingRun(
            id="mask-run-m10-1",
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=ds_v.id,
            source_dataset_digest="src_digest_m10",
            status=MaskingRunStatus.COMPLETED,
            created_by=user_owner.id,
        )
        db.add(mask_run)
        db.commit()

        gate1 = Gate1Approval(
            id="gate1-m10-1",
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=ds_v.id,
            masking_run_id=mask_run.id,
            source_dataset_digest="src_digest_m10",
            masked_output_digest="sha256:dsm10digest",
            findings_digest="find_digest_m10",
            reviewer_user_id=user_owner.id,
            reviewer_role_snapshot="WORKSPACE_OWNER",
            decision=Gate1Decision.APPROVED,
            signing_key_id="key1",
            approval_signature="sig1",
            canonical_payload="{}",
            reviewed_at=datetime.now(UTC),
        )
        db.add(gate1)
        db.commit()

        # 5. Seed Curated Models and Recipes
        sync_curated_model_catalog(db)
        sync_build_recipes(db)

    # 6. Issue Session Cookie for user_owner
    with Session(engine) as db:
        session = session_service.create_session(db, user_id=user_owner.id)
        db.commit()

    client.cookies.set("mizan_session", session.session_token)

    return {
        "engine": engine,
        "client": client,
        "ws_a_id": "ws-m10-a",
        "ws_b_id": "ws-m10-b",
        "user_owner_id": "usr-owner-m10",
        "user_other_id": "usr-other-m10",
        "dataset_id": "ds-m10-1",
        "dataset_version_id": "ds-v-m10-1",
        "gate1_approval_id": "gate1-m10-1",
        "csrf_token": session.csrf_token,
    }


# =========================================================================
# 1. Model Source and License Tests
# =========================================================================

def test_model_catalog_and_revision_resolution(m10_env):
    with Session(m10_env["engine"]) as db:
        models = db.query(ModelSource).all()
        assert len(models) >= 4

        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        assert tiny_model is not None
        assert tiny_model.license_status == LicenseStatus.VERIFIED_LICENSE
        assert tiny_model.is_gated is False

        # Immutable revision validation
        valid_sha = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
        assert resolve_model_revision(valid_sha) == valid_sha

        # Mutable branch reference rejected
        with pytest.raises(ValueError, match="Mutable revision reference 'main' is rejected"):
            resolve_model_revision("main")

        with pytest.raises(ValueError, match="Mutable revision reference 'master' is rejected"):
            resolve_model_revision("master")


def test_license_and_gated_access_evaluation():
    # Public Apache 2.0
    lic, acc, warns = validate_license_and_access("apache-2.0")
    assert lic == LicenseStatus.VERIFIED_LICENSE
    assert acc == ModelAccessStatus.PUBLIC
    assert len(warns) == 0

    # Llama community license (Restricted)
    lic, acc, warns = validate_license_and_access("llama-3.2-community", is_gated=True, hf_token_provided=False)
    assert lic == LicenseStatus.RESTRICTED_LICENSE
    assert acc == ModelAccessStatus.GATED_PENDING
    assert any("token is required" in w for w in warns)

    # Unknown license without user confirmation requires review
    lic, acc, warns = validate_license_and_access("unknown", user_confirmed_rights=False)
    assert lic == LicenseStatus.LICENSE_REVIEW_REQUIRED

    # Unknown license with explicit user rights confirmation
    lic, acc, warns = validate_license_and_access("unknown", user_confirmed_rights=True)
    assert lic == LicenseStatus.USER_CONFIRMED_RIGHTS


# =========================================================================
# 2. Dataset Preparation, Gate 1, and External Authorization Tests
# =========================================================================

def test_dataset_eligibility_and_gate1_enforcement(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        ds_id = m10_env["dataset_id"]
        ver_id = m10_env["dataset_version_id"]

        elig = verify_dataset_eligibility(db, ws_id, ds_id, ver_id)
        assert elig["is_eligible"] is True
        assert elig["gate1_approval_id"] == m10_env["gate1_approval_id"]


def test_external_processing_authorization_enforcement(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        ds_id = m10_env["dataset_id"]
        ver_id = m10_env["dataset_version_id"]

        # Colab export requires explicit external authorization
        with pytest.raises(Exception, match="requires explicit external processing authorization"):
            verify_dataset_eligibility(
                db, ws_id, ds_id, ver_id, require_external_authorization=True, external_authorization_id=None
            )

        # Create active authorization
        auth = ExternalProcessingAuthorization(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            dataset_id=ds_id,
            dataset_version_id=ver_id,
            dataset_version_digest="sha256:dsm10digest",
            purpose="Colab Free training",
            destination_class="GOOGLE_COLAB_EPHEMERAL_RUNTIME",
            authorized_by_user_id=m10_env["user_owner_id"],
            authorization_token="auth_token_123",
            expires_at=datetime.now(UTC) + timedelta(hours=12),
        )
        db.add(auth)
        db.commit()

        elig = verify_dataset_eligibility(
            db, ws_id, ds_id, ver_id, require_external_authorization=True, external_authorization_id=auth.id
        )
        assert elig["external_authorization_id"] == auth.id


def test_deterministic_train_val_partitions(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        ver_id = m10_env["dataset_version_id"]

        for i in range(10):
            doc = Document(
                dataset_version_id=ver_id,
                workspace_id=ws_id,
                name=f"doc_{i}.txt",
                file_type=DocumentFileType.TXT,
                mime_type="text/plain",
                raw_file_key=f"k_{i}",
                raw_file_size_bytes=100,
                raw_sha256=f"hash_{i}",
            )
            db.add(doc)
        db.commit()

        train_part, val_part = create_deterministic_train_val_partitions(db, ver_id, train_ratio=0.8, seed=42)
        assert train_part["record_count"] + val_part["record_count"] == 10
        assert train_part["record_count"] > 0
        assert val_part["record_count"] >= 1
        assert train_part["record_count"] + val_part["record_count"] == 10
        assert len(train_part["partition_digest"]) == 64

        # Identical partitions with same seed
        train2, val2 = create_deterministic_train_val_partitions(db, ver_id, train_ratio=0.8, seed=42)
        assert train_part["partition_digest"] == train2["partition_digest"]
        assert val_part["partition_digest"] == val2["partition_digest"]


# =========================================================================
# 3. Build Recipe and Architecture Validation Tests
# =========================================================================

def test_recipe_target_module_validation(m10_env):
    with Session(m10_env["engine"]) as db:
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "LORA_COLAB_FREE").first()
        assert recipe is not None

        # Valid Llama modules
        valid_cfg = {"lora_rank": 16, "lora_alpha": 32, "target_modules": ["q_proj", "v_proj"]}
        errors = validate_recipe_compatibility(recipe, "LlamaForCausalLM", valid_cfg)
        assert len(errors) == 0

        # Invalid module for LLaMA
        bad_cfg = {"lora_rank": 16, "lora_alpha": 32, "target_modules": ["c_attn"]}
        errors = validate_recipe_compatibility(recipe, "LlamaForCausalLM", bad_cfg)
        assert any("Target module 'c_attn' is invalid" in e for e in errors)

        # Invalid rank
        bad_rank_cfg = {"lora_rank": -4, "lora_alpha": 32}
        errors = validate_recipe_compatibility(recipe, "LlamaForCausalLM", bad_rank_cfg)
        assert any("Invalid lora_rank" in e for e in errors)


def test_gguf_conversion_preflight_and_requantization_block():
    # High-precision FP16 passes
    ok, errs = validate_gguf_conversion_preflight("FP16", ["Q8_0", "Q4_K_M"])
    assert ok is True
    assert len(errs) == 0

    # Requantization from Q4_K_M is blocked
    ok, errs = validate_gguf_conversion_preflight("Q4_K_M", ["Q8_0"])
    assert ok is False
    assert any("Requantization from already quantized weights" in e for e in errs)


def test_awq_quantization_separate_route():
    # AWQ without GPU fails
    ok, errs = validate_awq_quantization_preflight(
        architecture="LlamaForCausalLM",
        has_gpu=False,
        calibration_dataset_id="ds_123",
    )
    assert ok is False
    assert any("requires dedicated NVIDIA GPU" in e for e in errs)

    # AWQ without calibration dataset fails
    ok, errs = validate_awq_quantization_preflight(
        architecture="LlamaForCausalLM",
        has_gpu=True,
        calibration_dataset_id=None,
    )
    assert ok is False
    assert any("requires an authorized calibration dataset" in e for e in errs)

    # Valid AWQ with GPU & calibration dataset passes
    ok, errs = validate_awq_quantization_preflight(
        architecture="LlamaForCausalLM",
        has_gpu=True,
        calibration_dataset_id="ds_123",
    )
    assert ok is True


# =========================================================================
# 4. Resource Preflight Tests (Local 8 GB CPU Host vs Cloud GPU)
# =========================================================================

def test_resource_preflight_local_cpu_vs_gpu(m10_env):
    with Session(m10_env["engine"]) as db:
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        large_model = db.query(ModelSource).filter(ModelSource.model_key == "meta-llama/Llama-3.2-1B").first()
        smoke_recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()
        lora_recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "LORA_COLAB_FREE").first()

        # 1. Tiny model with SMOKE_TEST_CPU on local machine -> FEASIBLE
        res = run_build_preflight(
            model=tiny_model,
            recipe=smoke_recipe,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
        )
        assert res["is_feasible"] is True
        assert res["peak_memory_mb"] < 2048.0

        # 2. Large model on local machine with GPU recipe -> INFEASIBLE (CPU host & memory limit)
        res_large = run_build_preflight(
            model=large_model,
            recipe=lora_recipe,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
        )
        assert res_large["is_feasible"] is False
        assert any("local machine is CPU-only" in r for r in res_large["block_reasons"])

        # 3. Large model on Colab Free T4 (cloud_t4_16gb) -> FEASIBLE
        res_colab = run_build_preflight(
            model=large_model,
            recipe=lora_recipe,
            execution_mode=ExecutionMode.MANUAL_COLAB_NOTEBOOK,
            target_hardware_profile_key="NVIDIA_T4_16GB",
        )
        assert res_colab["is_feasible"] is True


# =========================================================================
# 5. Build Manifest & Checkpointing Tests
# =========================================================================

def test_build_manifest_determinism_and_hash_stability(m10_env):
    with Session(m10_env["engine"]) as db:
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()

        cfg = {"learning_rate": 0.0002, "max_steps": 5}
        m1, hash1 = generate_build_manifest(tiny_model, recipe, cfg)
        m2, hash2 = generate_build_manifest(tiny_model, recipe, cfg)
        assert hash1 == hash2
        assert len(hash1) == 64

        # Change hyperparameter -> hash must change
        _, hash3 = generate_build_manifest(tiny_model, recipe, {"learning_rate": 0.0005, "max_steps": 5})
        assert hash1 != hash3


def test_checkpointing_and_resume_verification(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        user_id = m10_env["user_owner_id"]
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()

        _, manifest_digest = generate_build_manifest(tiny_model, recipe, {})

        run = ModelBuildRun(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            created_by=user_id,
            name="Checkpoint Run",
            status=ModelBuildStatus.RUNNING,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
            source_model_id=tiny_model.id,
            source_revision=tiny_model.immutable_revision,
            recipe_id=recipe.id,
            recipe_key=recipe.recipe_key,
            manifest_digest=manifest_digest,
            train_partition_digest="train_dig_1",
        )
        db.add(run)
        db.commit()

        # Record checkpoint
        ckpt = record_checkpoint(
            db=db,
            build_run=run,
            checkpoint_number=1,
            step_number=50,
            epoch=1.0,
            metrics={"loss": 1.25},
            checkpoint_bytes=b"dummy_weights_step_50",
        )
        assert ckpt.sha256 is not None
        assert ckpt.step_number == 50

        # Resume with matching digest succeeds
        assert validate_resume_compatibility(run, manifest_digest, tiny_model.immutable_revision, "train_dig_1") is True

        # Resume with wrong manifest digest fails
        with pytest.raises(CheckpointError, match="manifest digest does not match"):
            validate_resume_compatibility(run, "wrong_digest_000000000000000000000000000000000000000000000000000000000000", tiny_model.immutable_revision)


# =========================================================================
# 6. Artifact Staging Tests (Pre-M11 Boundary)
# =========================================================================

def test_artifact_staging_integrity_and_m11_boundary(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        user_id = m10_env["user_owner_id"]
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "GGUF_CONVERT_AND_QUANTIZE").first()

        run = ModelBuildRun(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            created_by=user_id,
            name="GGUF Staging Run",
            status=ModelBuildStatus.RUNNING,
            execution_mode=ExecutionMode.MANUAL_COLAB_NOTEBOOK,
            source_model_id=tiny_model.id,
            source_revision=tiny_model.immutable_revision,
            recipe_id=recipe.id,
            recipe_key=recipe.recipe_key,
            manifest_digest="test_manifest_digest",
        )
        db.add(run)
        db.commit()

        # GGUF simulation
        sim_outputs = simulate_gguf_conversion_and_quantize(tiny_model.model_key, tiny_model.immutable_revision, ["Q8_0"])
        q8_meta = sim_outputs["Q8_0"]

        # Stage artifact
        staged = stage_model_artifact(
            db=db,
            build_run=run,
            artifact_type=ArtifactType.GGUF_Q8_0,
            format_name="GGUF",
            artifact_bytes=q8_meta["data_bytes"],
            expected_sha256=q8_meta["sha256"],
            quantization_type="Q8_0",
        )
        assert staged.sha256 == q8_meta["sha256"]
        # Verify M11 boundary: MUST be marked as staged, NOT released!
        assert staged.is_staged_for_m11 is True

        # Bad header rejection
        with pytest.raises(ArtifactStagingError, match="missing standard 'GGUF' magic byte"):
            stage_model_artifact(
                db=db,
                build_run=run,
                artifact_type=ArtifactType.GGUF_Q8_0,
                format_name="GGUF",
                artifact_bytes=b"CORRUPTED_HEADER_DATA",
            )


# =========================================================================
# 7. M6 Evaluation Linkage Tests
# =========================================================================

def test_model_evaluation_link_and_regression_visibility(m10_env):
    with Session(m10_env["engine"]) as db:
        ws_id = m10_env["ws_a_id"]
        user_id = m10_env["user_owner_id"]
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()

        run = ModelBuildRun(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            created_by=user_id,
            name="Eval Link Run",
            status=ModelBuildStatus.COMPLETED,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
            source_model_id=tiny_model.id,
            source_revision=tiny_model.immutable_revision,
            recipe_id=recipe.id,
            recipe_key=recipe.recipe_key,
            manifest_digest="eval_manifest_digest",
        )
        db.add(run)
        db.flush()

        artifact = StagedModelArtifact(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            build_run_id=run.id,
            artifact_type=ArtifactType.LORA_ADAPTER,
            format="SAFETENSORS",
            storage_reference="ref",
            file_size_bytes=1000,
            sha256="sha123",
            source_model_key=tiny_model.model_key,
            source_model_revision=tiny_model.immutable_revision,
            manifest_digest="eval_manifest_digest",
            is_staged_for_m11=True,
        )
        db.add(artifact)
        db.flush()

        # Create M6 Evaluation Suite and Run
        suite = EvaluationSuite(
            organization_id="org-m10-a",
            workspace_id=ws_id,
            created_by=user_id,
            name="Model Benchmark Suite",
            slug="benchmark-suite",
            status=EvaluationSuiteStatus.READY,
        )
        db.add(suite)
        db.flush()

        suite_ver = EvaluationSuiteVersion(
            suite_id=suite.id,
            version_number=1,
            suite_digest="suite_digest_abc_123",
            case_count=10,
            created_by=user_id,
        )
        db.add(suite_ver)
        db.flush()

        eval_run = EvaluationRun(
            organization_id="org-m10-a",
            suite_id=suite.id,
            suite_version_id=suite_ver.id,
            workspace_id=ws_id,
            created_by=user_id,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=0.72,
        )
        db.add(eval_run)
        db.commit()

        # Link evaluation with base score = 0.80 (shows a regression of -0.08)
        link = link_model_evaluation(
            db=db,
            build_run=run,
            staged_artifact=artifact,
            evaluation_run=eval_run,
            model_role=ModelRole.QUANTIZED_MODEL,
            base_evaluation_score=0.80,
        )
        assert link.overall_score == 0.72
        assert link.quality_delta == -0.08  # Regression visible, not concealed!
        summary = json.loads(link.comparison_summary_json)
        assert summary["is_regression"] is True


# =========================================================================
# 8. REST API & Tenant Isolation Tests
# =========================================================================

def test_api_create_build_run_and_local_execution(m10_env):
    client = m10_env["client"]
    ws_id = m10_env["ws_a_id"]
    csrf = m10_env["csrf_token"]

    with Session(m10_env["engine"]) as db:
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()
        model_id = tiny_model.id
        recipe_id = recipe.id

    # 1. Create build run
    payload = {
        "name": "Integration Test Build",
        "description": "Testing local CPU smoke test via REST API",
        "source_model_id": model_id,
        "recipe_id": recipe_id,
        "execution_mode": "LOCAL_SMOKE_TEST",
        "training_config": {"learning_rate": 0.0002, "max_steps": 4},
    }
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/model-building/runs",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    run_id = data["id"]
    assert data["status"] == "READY"
    assert data["manifest_digest"] is not None

    # 2. Execute local CPU smoke test
    exec_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/model-building/runs/{run_id}/execute-local",
        headers={"X-CSRF-Token": csrf},
    )
    assert exec_resp.status_code == 200, exec_resp.text
    exec_data = exec_resp.json()
    assert exec_data["status"] == "COMPLETED"
    assert len(exec_data["checkpoints"]) >= 2
    assert len(exec_data["staged_artifacts"]) >= 1

    # 3. Export Colab notebook for the run
    export_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/model-building/runs/{run_id}/export-notebook",
    )
    assert export_resp.status_code == 200
    nb = json.loads(export_resp.content.decode("utf-8"))
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) >= 5


def test_api_tenant_isolation_anti_enumeration(m10_env):
    client = m10_env["client"]
    ws_a_id = m10_env["ws_a_id"]
    ws_b_id = m10_env["ws_b_id"]
    csrf = m10_env["csrf_token"]

    with Session(m10_env["engine"]) as db:
        tiny_model = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()
        model_id = tiny_model.id
        recipe_id = recipe.id

    # Create run in ws A
    payload = {
        "name": "Tenant Run A",
        "source_model_id": model_id,
        "recipe_id": recipe_id,
        "execution_mode": "LOCAL_SMOKE_TEST",
        "training_config": {},
    }
    resp = client.post(
        f"/api/v1/workspaces/{ws_a_id}/model-building/runs",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    run_id = resp.json()["id"]

    # Accessing via foreign workspace must return 404 (Anti-Enumeration)
    cross_resp = client.get(
        f"/api/v1/workspaces/{ws_b_id}/model-building/runs/{run_id}",
    )
    assert cross_resp.status_code == 404
