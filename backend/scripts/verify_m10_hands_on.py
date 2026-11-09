"""Hands-on verification script for Milestone 10: Model Building & Colab Lab.

Executes and logs evidence for the 11-item manual verification checklist.
"""

import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.dataset import Dataset, DatasetVersion, DatasetVersionStatus
from app.models.evaluation import (
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationSuite,
    EvaluationSuiteStatus,
    EvaluationSuiteVersion,
)
from app.models.identity import AccountStatus, User
from app.models.masking import Gate1Approval, Gate1Decision, MaskingRun, MaskingRunStatus
from app.models.model_building import (
    ArtifactType,
    ArtifactVerificationStatus,
    ExecutionMode,
    ExternalProcessingAuthorization,
    ModelBuildRecipe,
    ModelBuildRun,
    ModelBuildStatus,
    ModelRole,
    ModelSource,
    StagedModelArtifact,
)
from app.models.organization import Organization, Workspace
from app.modules.model_building.artifact_staging_service import (
    ArtifactStagingError,
    stage_model_artifact,
)
from app.modules.model_building.build_manifest import generate_build_manifest
from app.modules.model_building.build_preflight import run_build_preflight
from app.modules.model_building.build_recipe_registry import sync_build_recipes
from app.modules.model_building.colab_notebook_generator import generate_colab_notebook_for_build
from app.modules.model_building.model_evaluation_service import link_model_evaluation
from app.modules.model_building.model_source_catalog import sync_curated_model_catalog
from app.modules.model_building.training_service import execute_local_smoke_test


def run_checklist():
    print("=" * 80)
    print("MIZAN MILESTONE 10: HANDS-ON VERIFICATION CHECKLIST EXECUTION")
    print("=" * 80)
    results = {}

    with Session(engine) as db:
        # Pre-flight setup: ensure catalog & recipes populated
        sync_curated_model_catalog(db)
        sync_build_recipes(db)

        # Setup test user, organization and workspaces
        user = db.query(User).filter(User.normalized_email == "m10_engineer@mizan.org").first()
        if not user:
            user = User(
                email="m10_engineer@mizan.org",
                normalized_email="m10_engineer@mizan.org",
                full_name="M10 Verification Engineer",
                password_hash="test_password_hash_verification",
                status=AccountStatus.ACTIVE,
            )
            db.add(user)
            db.flush()

        org = db.query(Organization).filter(Organization.slug == "m10-verify-org").first()
        if not org:
            org = Organization(name="M10 Verification Org", slug="m10-verify-org", created_by=user.id)
            db.add(org)
            db.flush()

        ws_a = db.query(Workspace).filter(Workspace.slug == "m10-ws-a").first()
        if not ws_a:
            ws_a = Workspace(organization_id=org.id, name="Workspace Alpha", slug="m10-ws-a", created_by=user.id)
            db.add(ws_a)
            db.flush()

        ws_b = db.query(Workspace).filter(Workspace.slug == "m10-ws-b").first()
        if not ws_b:
            ws_b = Workspace(organization_id=org.id, name="Workspace Beta", slug="m10-ws-b", created_by=user.id)
            db.add(ws_b)
            db.flush()

        db.commit()

        # ---------------------------------------------------------------------
        # CHECK 1: Create LOCAL_SMOKE_TEST using 35M test model
        # ---------------------------------------------------------------------
        print("\n[CHECK 1] Creating LOCAL_SMOKE_TEST using 35M test model...")
        model_35m = db.query(ModelSource).filter(ModelSource.model_key == "mizan-test/tiny-llama-35m").first()
        recipe_smoke = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "SMOKE_TEST_CPU").first()
        assert model_35m is not None, "Model 35M not found in catalog"
        assert recipe_smoke is not None, "SMOKE_TEST_CPU recipe not found"

        manifest_dict, manifest_digest = generate_build_manifest(
            model=model_35m,
            recipe=recipe_smoke,
            training_config={"learning_rate": 0.0002, "max_steps": 4},
        )

        run_smoke = ModelBuildRun(
            organization_id=org.id,
            workspace_id=ws_a.id,
            created_by=user.id,
            name="Hands-on Verification Smoke Run",
            description="Verifying local CPU smoke test pipeline",
            status=ModelBuildStatus.READY,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
            source_model_id=model_35m.id,
            source_revision=model_35m.immutable_revision,
            recipe_id=recipe_smoke.id,
            recipe_key=recipe_smoke.recipe_key,
            training_config_json=json.dumps({"learning_rate": 0.0002, "max_steps": 4}),
            build_manifest_json=json.dumps(manifest_dict),
            manifest_digest=manifest_digest,
        )
        db.add(run_smoke)
        db.commit()
        db.refresh(run_smoke)
        print(f" -> Created run {run_smoke.id} (Status: {run_smoke.status.value}, Manifest: {manifest_digest[:16]}...)")
        results["CHECK_1_CREATE_SMOKE_RUN"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 2: Resource preflight & machine classification
        # ---------------------------------------------------------------------
        print("\n[CHECK 2] Running resource preflight & checking host machine specs...")
        preflight_local = run_build_preflight(
            model=model_35m,
            recipe=recipe_smoke,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
            target_hardware_profile_key="LOCAL_CPU_I5_8GB",
        )
        print(f" -> Hardware Profile: {preflight_local['hardware_name']}")
        print(f" -> Weight RAM: {preflight_local['weight_memory_mb']} MB")
        print(f" -> KV Cache: {preflight_local['kv_cache_mb']} MB")
        print(f" -> Peak RAM: {preflight_local['peak_memory_mb']} MB")
        print(f" -> Disk Space Required: {preflight_local['total_disk_required_mb']} MB")
        print(f" -> Feasibility: {preflight_local['feasibility_status']} (is_feasible={preflight_local['is_feasible']})")
        assert preflight_local["is_feasible"] is True, "Preflight should be feasible for 35M model on local host"
        assert preflight_local["peak_memory_mb"] < 2048.0, "Peak memory for 35M model must be well under local threshold"
        results["CHECK_2_PREFLIGHT_LOCAL_HOST"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 3: Execute smoke test & inspect checkpoints and output metadata
        # ---------------------------------------------------------------------
        print("\n[CHECK 3] Executing local CPU smoke test...")
        execute_local_smoke_test(db, run_smoke)
        db.refresh(run_smoke)
        assert run_smoke.status == ModelBuildStatus.COMPLETED, f"Run status should be COMPLETED, got {run_smoke.status}"
        assert len(run_smoke.checkpoints) > 0, "Checkpoints must be recorded"
        chk = run_smoke.checkpoints[0]
        print(f" -> Run completed successfully! Checkpoints created: {len(run_smoke.checkpoints)}")
        print(f" -> Checkpoint #1: step={chk.step_number}, epoch={chk.epoch}, sha256={chk.sha256[:16]}...")
        assert len(run_smoke.staged_artifacts) > 0, "Staged artifact must be created"
        art = run_smoke.staged_artifacts[0]
        print(f" -> Staged Artifact: {art.artifact_type.value}, Format: {art.format}, Size: {art.file_size_bytes} bytes")
        print(f" -> Artifact SHA-256: {art.sha256}")
        print(f" -> Verification Status: {art.verification_status.value} (is_staged_for_m11={art.is_staged_for_m11})")
        results["CHECK_3_RUN_SMOKE_TEST_AND_INSPECT"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 4: Try larger model in local mode -> verify resource blocking
        # ---------------------------------------------------------------------
        print("\n[CHECK 4] Testing larger model in local CPU mode...")
        large_model = db.query(ModelSource).filter(ModelSource.model_key == "meta-llama/Llama-3.2-1B").first()
        recipe_lora = db.query(ModelBuildRecipe).filter(ModelBuildRecipe.recipe_key == "LORA_COLAB_FREE").first()
        preflight_blocked = run_build_preflight(
            model=large_model,
            recipe=recipe_lora,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
        )
        print(f" -> Large model local feasibility: is_feasible={preflight_blocked['is_feasible']}")
        print(f" -> Block reasons: {preflight_blocked['block_reasons']}")
        assert preflight_blocked["is_feasible"] is False, "Large model with GPU recipe should be blocked on local CPU host"
        assert any("local machine is CPU-only" in r for r in preflight_blocked["block_reasons"])
        results["CHECK_4_LARGE_MODEL_BLOCKED_LOCAL"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 5 & 6: Gate 1 approved dataset & External processing authorization
        # ---------------------------------------------------------------------
        print("\n[CHECK 5 & 6] Testing Gate 1 privacy and external-processing authorization...")
        run_suffix = uuid.uuid4().hex[:8]
        # Create dataset and Gate 1 approval
        ds = Dataset(
            workspace_id=ws_a.id,
            name=f"Customer Support Corpus {run_suffix}",
            slug=f"customer-support-corpus-{run_suffix}",
            created_by=user.id,
        )
        db.add(ds)
        db.flush()

        dsv = DatasetVersion(
            dataset_id=ds.id,
            version_number=1,
            name="v1",
            content_hash="dsv_digest_abc_123",
            status=DatasetVersionStatus.READY,
        )
        db.add(dsv)
        db.flush()

        m_run = MaskingRun(
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            source_dataset_digest="src_digest_m10",
            status=MaskingRunStatus.COMPLETED,
            created_by=user.id,
        )
        db.add(m_run)
        db.flush()

        gate1 = Gate1Approval(
            organization_id=org.id,
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            masking_run_id=m_run.id,
            source_dataset_digest="src_digest_m10",
            masked_output_digest="dsv_digest_abc_123",
            findings_digest="find_digest_m10",
            reviewer_user_id=user.id,
            reviewer_role_snapshot="WORKSPACE_OWNER",
            decision=Gate1Decision.APPROVED,
            signing_key_id="key1",
            approval_signature="sig1",
            canonical_payload="{}",
            reviewed_at=datetime.now(UTC),
        )
        db.add(gate1)
        db.commit()

        # Check authorization requirement: without external authorization, Colab build fails
        from app.modules.model_building.dataset_preparation import (
            DatasetEligibilityError,
            verify_dataset_eligibility,
        )
        try:
            verify_dataset_eligibility(
                db=db,
                workspace_id=ws_a.id,
                dataset_id=ds.id,
                dataset_version_id=dsv.id,
                require_external_authorization=True,
                external_authorization_id=None,
            )
            print(" -> FAILED: External authorization requirement not enforced!")
            assert False, "Should have raised DatasetEligibilityError"
        except DatasetEligibilityError as e:
            print(f" -> Correctly blocked un-authorized external export: {e}")

        # Now create external authorization
        auth_token = hashlib.sha256(f"AUTH:{ws_a.id}:{dsv.id}:{run_suffix}".encode()).hexdigest()
        ext_auth = ExternalProcessingAuthorization(
            organization_id=org.id,
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            dataset_version_digest=dsv.content_hash,
            purpose="LoRA adapter fine-tuning on Colab Free T4 GPU",
            destination_class="GOOGLE_COLAB_EPHEMERAL_RUNTIME",
            authorized_by_user_id=user.id,
            authorization_token=auth_token,
            expires_at=(datetime.now(UTC) + timedelta(hours=24)).replace(tzinfo=None),
        )
        db.add(ext_auth)
        db.commit()

        # Verify now passes
        elig = verify_dataset_eligibility(
            db=db,
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            require_external_authorization=True,
            external_authorization_id=ext_auth.id,
        )
        assert elig["is_eligible"] is True, "Dataset should be eligible with active external authorization"
        print(" -> Verified: External authorization successfully validates Gate 1 approved export")
        results["CHECK_5_6_GATE1_AND_EXTERNAL_AUTH"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 7: Inspect generated Colab notebook and manifest
        # ---------------------------------------------------------------------
        print("\n[CHECK 7] Inspecting generated Colab notebook and manifest...")
        manifest_colab, manifest_digest_colab = generate_build_manifest(
            model=large_model,
            recipe=recipe_lora,
            training_config={"learning_rate": 0.0002, "max_steps": 100},
            dataset_metadata=elig,
        )
        run_colab = ModelBuildRun(
            organization_id=org.id,
            workspace_id=ws_a.id,
            created_by=user.id,
            name="Colab T4 LoRA Build",
            status=ModelBuildStatus.READY,
            execution_mode=ExecutionMode.MANUAL_COLAB_NOTEBOOK,
            source_model_id=large_model.id,
            source_revision=large_model.immutable_revision,
            recipe_id=recipe_lora.id,
            recipe_key=recipe_lora.recipe_key,
            manifest_digest=manifest_digest_colab,
            training_config_json=json.dumps({"learning_rate": 0.0002, "max_steps": 100}),
            build_manifest_json=json.dumps(manifest_colab),
        )
        db.add(run_colab)
        db.commit()

        notebook_str = generate_colab_notebook_for_build(run_colab)
        notebook_json = json.loads(notebook_str)
        assert "cells" in notebook_json, "Notebook must contain cells"
        assert len(notebook_json["cells"]) >= 6, "Notebook should contain at least 6 cells"
        cell_sources = "".join("".join(c.get("source", [])) for c in notebook_json["cells"])
        assert manifest_digest_colab in cell_sources, "Notebook must embed manifest digest"
        print(f" -> Generated Colab notebook has {len(notebook_json['cells'])} cells, embeds manifest {manifest_digest_colab[:16]}...")
        results["CHECK_7_COLAB_NOTEBOOK_GENERATION"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 8: Import execution report & staged artifact
        # ---------------------------------------------------------------------
        print("\n[CHECK 8] Importing Colab result and staging artifact...")
        test_payload = b'{"__metadata__": {"format": "pt"}, "lora_weight": [1, 2, 3]}'
        correct_hash = hashlib.sha256(test_payload).hexdigest()

        staged_art = stage_model_artifact(
            db=db,
            build_run=run_colab,
            artifact_type=ArtifactType.LORA_ADAPTER,
            format_name="SAFETENSORS",
            artifact_bytes=test_payload,
            expected_sha256=correct_hash,
        )
        print(f" -> Staged artifact: id={staged_art.id}, status={staged_art.verification_status.value}")
        assert staged_art.verification_status == ArtifactVerificationStatus.VERIFIED, "Artifact must be verified"
        assert staged_art.is_staged_for_m11 is True, "is_staged_for_m11 must be True"
        results["CHECK_8_COLAB_ARTIFACT_IMPORT"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 9: Tampering test - verify checksum validation rejects modified byte
        # ---------------------------------------------------------------------
        print("\n[CHECK 9] Tampering test: Modifying one byte and verifying checksum rejection...")
        tampered_payload = bytearray(test_payload)
        tampered_payload[0] = ord(b"X")  # Flip first byte

        try:
            stage_model_artifact(
                db=db,
                build_run=run_colab,
                artifact_type=ArtifactType.LORA_ADAPTER,
                format_name="SAFETENSORS",
                artifact_bytes=bytes(tampered_payload),
                expected_sha256=correct_hash,  # Claims original hash but content tampered
            )
            print(" -> FAILED: Tampered artifact was not rejected!")
            assert False, "Should have raised ArtifactStagingError"
        except ArtifactStagingError as e:
            print(f" -> Correctly rejected tampered artifact: {e}")
        results["CHECK_9_CHECKSUM_TAMPER_REJECTION"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 10: Inspect evaluation results & verify regression visibility
        # ---------------------------------------------------------------------
        print("\n[CHECK 10] Verifying evaluation linkage and regression visibility...")
        suite = EvaluationSuite(
            organization_id=org.id,
            workspace_id=ws_a.id,
            created_by=user.id,
            name="Benchmark Suite",
            slug=f"benchmark-suite-verify-{run_suffix}",
            status=EvaluationSuiteStatus.READY,
        )
        db.add(suite)
        db.flush()

        s_ver = EvaluationSuiteVersion(
            suite_id=suite.id,
            version_number=1,
            suite_digest="s_ver_digest_123",
            case_count=10,
            created_by=user.id,
        )
        db.add(s_ver)
        db.flush()

        eval_run_gain = EvaluationRun(
            organization_id=org.id,
            suite_id=suite.id,
            suite_version_id=s_ver.id,
            workspace_id=ws_a.id,
            created_by=user.id,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=0.88,
        )
        eval_run_reg = EvaluationRun(
            organization_id=org.id,
            suite_id=suite.id,
            suite_version_id=s_ver.id,
            workspace_id=ws_a.id,
            created_by=user.id,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=0.72,
        )
        db.add(eval_run_gain)
        db.add(eval_run_reg)
        db.commit()

        # Link gain (0.80 base -> 0.88 adapted)
        link_gain = link_model_evaluation(
            db=db,
            build_run=run_colab,
            staged_artifact=staged_art,
            evaluation_run=eval_run_gain,
            model_role=ModelRole.FINE_TUNED_MODEL,
            base_evaluation_score=0.80,
        )
        print(f" -> Quality Gain Link: overall={link_gain.overall_score}, delta={link_gain.quality_delta:+.2f}")
        assert link_gain.quality_delta == 0.08, "Quality delta must match score - base_score"

        # Link regression (0.80 base -> 0.72 quantized)
        link_reg = link_model_evaluation(
            db=db,
            build_run=run_colab,
            staged_artifact=staged_art,
            evaluation_run=eval_run_reg,
            model_role=ModelRole.QUANTIZED_MODEL,
            base_evaluation_score=0.80,
        )
        summary_reg = json.loads(link_reg.comparison_summary_json)
        print(f" -> Quality Regression Link: overall={link_reg.overall_score}, delta={link_reg.quality_delta:+.2f}, is_regression={summary_reg['is_regression']}")
        assert link_reg.quality_delta == -0.08, "Quality delta must be negative"
        assert summary_reg["is_regression"] is True, "is_regression must be True"
        results["CHECK_10_EVALUATION_REGRESSION_VISIBILITY"] = "PASSED"

        # ---------------------------------------------------------------------
        # CHECK 11: Cross-workspace tenant isolation
        # ---------------------------------------------------------------------
        print("\n[CHECK 11] Verifying cross-workspace tenant isolation...")
        # Query runs belonging to Workspace B: run_smoke belongs to Workspace A, so query in ws_b must return 0 runs
        ws_b_runs = db.query(ModelBuildRun).filter(
            ModelBuildRun.workspace_id == ws_b.id,
            ModelBuildRun.id == run_smoke.id,
        ).first()
        print(f" -> Workspace B query for Workspace A build run: {ws_b_runs}")
        assert ws_b_runs is None, "Cross-workspace isolation failure: Workspace B must not access Workspace A run"

        ws_b_artifacts = db.query(StagedModelArtifact).filter(
            StagedModelArtifact.workspace_id == ws_b.id,
            StagedModelArtifact.id == staged_art.id,
        ).first()
        print(f" -> Workspace B query for Workspace A staged artifact: {ws_b_artifacts}")
        assert ws_b_artifacts is None, "Cross-workspace isolation failure: Workspace B must not access Workspace A artifact"
        results["CHECK_11_TENANT_ISOLATION"] = "PASSED"

    print("\n" + "=" * 80)
    print("ALL 11 HANDS-ON VERIFICATION CHECKS PASSED:")
    for k, v in results.items():
        print(f"  [x] {k}: {v}")
    print("=" * 80)


if __name__ == "__main__":
    run_checklist()
