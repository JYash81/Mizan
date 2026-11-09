"""Tests for Milestone 11: Artifact Registry, Release Management, Cryptographic Integrity & Gate 3 Approval."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.artifact_registry import (
    Gate3Decision,
    ModelFamilyStatus,
    ModelVersionStatus,
    RegisteredArtifactType,
)
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
    LicenseStatus,
    ModelAccessStatus,
    ModelBuildRecipe,
    ModelBuildRun,
    ModelBuildStatus,
    ModelSource,
    RecipeType,
    StagedModelArtifact,
)
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.modules.artifact_registry.exceptions import (
    ArtifactRegistryError,
    ImmutableReleaseError,
    ReleaseNotFoundError,
    SeparationOfDutiesViolationError,
    SignaturePurposeMismatchError,
)
from app.modules.artifact_registry.gate3_service import (
    revoke_model_release,
    submit_gate3_decision,
    verify_gate3_attestation,
)
from app.modules.artifact_registry.manifest_service import (
    verify_release_manifest_integrity,
)
from app.modules.artifact_registry.provenance_service import verify_model_provenance
from app.modules.artifact_registry.registry_service import (
    create_model_family,
    create_model_version,
    finalize_model_version_manifest,
    get_model_family,
    list_model_families,
    register_staged_artifact,
)


@pytest.fixture
def m11_env():
    """Seed test fixtures for M11."""
    run_id = uuid.uuid4().hex[:6]
    with Session(engine) as db:
        # Users: Creator and Reviewer for separation of duties
        creator = User(
            id=f"user-creator-{run_id}",
            email=f"creator_{run_id}@mizan.org",
            normalized_email=f"creator_{run_id}@mizan.org",
            full_name="Model Builder Engineer",
            password_hash="test_hash_safe",
            status=AccountStatus.ACTIVE,
        )
        reviewer = User(
            id=f"user-reviewer-{run_id}",
            email=f"reviewer_{run_id}@mizan.org",
            normalized_email=f"reviewer_{run_id}@mizan.org",
            full_name="Compliance Approver",
            password_hash="test_hash_safe",
            status=AccountStatus.ACTIVE,
        )
        db.add_all([creator, reviewer])
        db.flush()

        # Organization & Workspace A
        org = Organization(
            id=f"org-m11-{run_id}",
            name=f"M11 Corp {run_id}",
            slug=f"m11-corp-{run_id}",
            created_by=reviewer.id,
        )
        db.add(org)
        db.flush()

        ws_a = Workspace(
            id=f"ws-m11-a-{run_id}",
            organization_id=org.id,
            name=f"Workspace A {run_id}",
            slug=f"ws-m11-a-{run_id}",
            created_by=reviewer.id,
        )
        ws_b = Workspace(
            id=f"ws-m11-b-{run_id}",
            organization_id=org.id,
            name=f"Workspace B {run_id}",
            slug=f"ws-m11-b-{run_id}",
            created_by=reviewer.id,
        )
        db.add_all([ws_a, ws_b])
        db.flush()

        # Memberships: Creator is MEMBER, Reviewer is OWNER
        db.add(OrganizationMembership(
            organization_id=org.id,
            user_id=reviewer.id,
            role=OrganizationRole.OWNER,
        ))
        db.add(OrganizationMembership(
            organization_id=org.id,
            user_id=creator.id,
            role=OrganizationRole.MEMBER,
        ))
        db.add(WorkspaceMembership(
            workspace_id=ws_a.id,
            user_id=creator.id,
            role=WorkspaceRole.WORKSPACE_MEMBER,
        ))
        db.add(WorkspaceMembership(
            workspace_id=ws_a.id,
            user_id=reviewer.id,
            role=WorkspaceRole.WORKSPACE_OWNER,
        ))
        db.flush()

        # Curated Model Source
        model_source = ModelSource(
            id=f"src-m11-{run_id}",
            model_key=f"mizan/test-llama-{run_id}",
            name="Test Llama 3B",
            immutable_revision="rev-sha-12345",
            architecture="LlamaForCausalLM",
            parameter_count_millions=3000.0,
            license_id="apache-2.0",
            license_status=LicenseStatus.VERIFIED_LICENSE,
            commercial_use_allowed=True,
            access_status=ModelAccessStatus.PUBLIC,
            is_active=True,
        )
        db.add(model_source)

        # Build Recipe
        recipe_key = f"LORA_TEST_RECIPE_{run_id}"
        recipe = ModelBuildRecipe(
            id=f"rec-m11-{run_id}",
            recipe_key=recipe_key,
            recipe_version="1.0.0",
            recipe_type=RecipeType.LORA_FINETUNE,
            name="LoRA Test Recipe",
            description="Test LoRA recipe",
        )
        db.add(recipe)
        db.flush()

        # Dataset & Gate 1
        ds = Dataset(
            id=f"ds-m11-{run_id}",
            workspace_id=ws_a.id,
            name=f"Dataset {run_id}",
            slug=f"dataset-{run_id}",
            created_by=creator.id,
        )
        db.add(ds)
        db.flush()

        dsv = DatasetVersion(
            id=f"dsv-m11-{run_id}",
            dataset_id=ds.id,
            version_number=1,
            name="v1",
            content_hash="dsv_hash_112233",
            status=DatasetVersionStatus.READY,
        )
        db.add(dsv)
        db.flush()

        m_run = MaskingRun(
            id=f"mrun-m11-{run_id}",
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            source_dataset_digest="src_digest_m11",
            status=MaskingRunStatus.COMPLETED,
            created_by=creator.id,
        )
        db.add(m_run)
        db.flush()

        gate1 = Gate1Approval(
            id=f"gate1-m11-{run_id}",
            organization_id=org.id,
            workspace_id=ws_a.id,
            dataset_id=ds.id,
            dataset_version_id=dsv.id,
            masking_run_id=m_run.id,
            source_dataset_digest="src_digest_m11",
            masked_output_digest="dsv_hash_112233",
            findings_digest="find_digest_m11",
            reviewer_user_id=reviewer.id,
            reviewer_role_snapshot="WORKSPACE_OWNER",
            decision=Gate1Decision.APPROVED,
            signing_key_id="mizan-platform-dev-01",
            approval_signature="gate1_sig_hex",
            canonical_payload="{}",
            reviewed_at=datetime.now(UTC),
        )
        db.add(gate1)
        db.flush()

        # Model Build Run & Staged Artifact
        build_run = ModelBuildRun(
            id=f"build-run-m11-{run_id}",
            organization_id=org.id,
            workspace_id=ws_a.id,
            created_by=creator.id,
            name=f"Build Run {run_id}",
            status=ModelBuildStatus.COMPLETED,
            execution_mode=ExecutionMode.LOCAL_SMOKE_TEST,
            source_model_id=model_source.id,
            source_revision=model_source.immutable_revision,
            recipe_id=recipe.id,
            recipe_key=recipe.recipe_key,
            manifest_digest="build_manifest_digest_abc",
        )
        db.add(build_run)
        db.flush()

        staged_art = StagedModelArtifact(
            id=f"staged-art-m11-{run_id}",
            organization_id=org.id,
            workspace_id=ws_a.id,
            build_run_id=build_run.id,
            artifact_type=ArtifactType.LORA_ADAPTER,
            format="SAFETENSORS",
            storage_reference=f"workspaces/{ws_a.id}/staged/adapter.safetensors",
            file_size_bytes=1024,
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            source_model_key=model_source.model_key,
            source_model_revision=model_source.immutable_revision,
            manifest_digest="build_manifest_digest_abc",
            verification_status=ArtifactVerificationStatus.VERIFIED,
            is_staged_for_m11=True,
        )
        db.add(staged_art)
        db.flush()

        # Evaluation Suite & Run
        eval_suite = EvaluationSuite(
            id=f"suite-m11-{run_id}",
            organization_id=org.id,
            workspace_id=ws_a.id,
            created_by=creator.id,
            name="M11 Benchmark Suite",
            slug=f"m11-suite-{run_id}",
            status=EvaluationSuiteStatus.READY,
        )
        db.add(eval_suite)
        db.flush()

        eval_ver = EvaluationSuiteVersion(
            id=f"sver-m11-{run_id}",
            suite_id=eval_suite.id,
            version_number=1,
            suite_digest="sver_digest_m11",
            case_count=10,
            created_by=creator.id,
        )
        db.add(eval_ver)
        db.flush()

        eval_run = EvaluationRun(
            id=f"eval-run-m11-{run_id}",
            organization_id=org.id,
            workspace_id=ws_a.id,
            suite_id=eval_suite.id,
            suite_version_id=eval_ver.id,
            created_by=creator.id,
            status=EvaluationRunStatus.COMPLETED,
            overall_score=0.88,
        )
        db.add(eval_run)
        db.commit()

        return {
            "run_id": run_id,
            "creator_id": creator.id,
            "reviewer_id": reviewer.id,
            "org_id": org.id,
            "ws_a_id": ws_a.id,
            "ws_b_id": ws_b.id,
            "model_key": model_source.model_key,
            "immutable_revision": model_source.immutable_revision,
            "recipe_key": recipe.recipe_key,
            "dataset_id": ds.id,
            "dataset_version_id": dsv.id,
            "dataset_version_digest": dsv.content_hash,
            "gate1_id": gate1.id,
            "build_run_id": build_run.id,
            "staged_art_id": staged_art.id,
            "eval_run_id": eval_run.id,
        }


# =========================================================================
# 1. Model Family & Version Lifecycle Tests
# =========================================================================


def test_model_family_lifecycle(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        user_id = m11_env["creator_id"]

        slug = f"support-llm-{uuid.uuid4().hex[:6]}"
        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            name="Customer Support LLM",
            slug=slug,
            description="Domain tuned support agent",
            task_type="TEXT_GENERATION",
        )
        assert family.id is not None
        assert family.status == ModelFamilyStatus.ACTIVE

        # Duplicate slug rejection
        with pytest.raises(ArtifactRegistryError, match="already exists"):
            create_model_family(
                db=db,
                workspace_id=ws_id,
                organization_id=org_id,
                user_id=user_id,
                name="Duplicate",
                slug=slug,
            )

        # List families
        families = list_model_families(db, ws_id)
        assert len(families) >= 1
        assert any(f.slug == slug for f in families)


def test_model_version_creation_and_unique_tag(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        user_id = m11_env["creator_id"]

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            name="Code Assistant",
            slug=f"code-asst-{uuid.uuid4().hex[:6]}",
        )

        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=user_id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        assert version.status == ModelVersionStatus.DRAFT
        assert version.version_tag == "v1.0.0"
        assert not version.is_immutable

        # Duplicate tag in same family rejected
        with pytest.raises(ArtifactRegistryError, match="already exists"):
            create_model_version(
                db=db,
                workspace_id=ws_id,
                organization_id=org_id,
                family_id=family.id,
                user_id=user_id,
                version_tag="v1.0.0",
                source_model_key=m11_env["model_key"],
                source_model_revision=m11_env["immutable_revision"],
                recipe_key=m11_env["recipe_key"],
            )


# =========================================================================
# 2. Staged Artifact Promotion & Deduplication
# =========================================================================


def test_staged_artifact_promotion(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        user_id = m11_env["creator_id"]
        staged_id = m11_env["staged_art_id"]

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            name="Promote Family",
            slug=f"promote-{uuid.uuid4().hex[:6]}",
        )

        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=user_id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )

        reg_art = register_staged_artifact(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            staged_artifact_id=staged_id,
            is_primary_weights=True,
        )
        assert reg_art.id is not None
        assert reg_art.artifact_type == RegisteredArtifactType.LORA_ADAPTER
        assert reg_art.is_primary_weights is True

        # Re-registering same artifact is idempotent
        reg_art_again = register_staged_artifact(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            staged_artifact_id=staged_id,
        )
        assert reg_art_again.id == reg_art.id


# =========================================================================
# 3. 5-Pillar Provenance Verification Tests
# =========================================================================


def test_provenance_verification_success(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]

        res = verify_model_provenance(
            db=db,
            workspace_id=ws_id,
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
            build_run_id=m11_env["build_run_id"],
            dataset_id=m11_env["dataset_id"],
            dataset_version_id=m11_env["dataset_version_id"],
            dataset_version_digest=m11_env["dataset_version_digest"],
            gate1_approval_id=m11_env["gate1_id"],
            evaluation_run_id=m11_env["eval_run_id"],
            base_evaluation_score=0.80,
            final_evaluation_score=0.88,
            min_ram_mb=4096.0,
            min_vram_mb=8192.0,
            target_hardware_key="LOCAL_CPU_I5_8GB",
        )
        assert res["is_valid"] is True
        assert len(res["blockers"]) == 0
        assert res["quality_delta"] == 0.08
        assert "BASE_MODEL_LICENSE" in res["checks"]
        assert "DATASET_GATE1_DATA_RIGHTS" in res["checks"]
        assert "BUILD_MANIFEST_PROVENANCE" in res["checks"]
        assert "EVALUATION_EVIDENCE" in res["checks"]
        assert "HARDWARE_FEASIBILITY" in res["checks"]


def test_provenance_verification_blocked_without_gate1(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]

        # Deliberately point to non-existent gate 1 approval
        res = verify_model_provenance(
            db=db,
            workspace_id=ws_id,
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
            dataset_id=m11_env["dataset_id"],
            dataset_version_id=m11_env["dataset_version_id"],
            gate1_approval_id="non-existent-gate1",
        )
        assert res["is_valid"] is False
        assert any("Gate 1" in b for b in res["blockers"])


# =========================================================================
# 4. Release Manifest Generation & Tamper Detection
# =========================================================================


def test_release_manifest_generation_and_tampering(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        user_id = m11_env["creator_id"]
        staged_id = m11_env["staged_art_id"]

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            name="Manifest Family",
            slug=f"manifest-{uuid.uuid4().hex[:6]}",
        )
        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=user_id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        register_staged_artifact(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            staged_artifact_id=staged_id,
        )

        version_final, digest = finalize_model_version_manifest(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            user_id=user_id,
        )
        assert version_final.status == ModelVersionStatus.PENDING_REVIEW
        assert version_final.release_manifest_digest == digest
        assert len(digest) == 64

        # Verify integrity succeeds with valid manifest
        assert verify_release_manifest_integrity(version_final.release_manifest_json, digest) is True

        # Tampering test: alter one field in manifest
        tampered_manifest = json.loads(version_final.release_manifest_json)
        tampered_manifest["version_tag"] = "v1.0.0-TAMPERED"
        assert verify_release_manifest_integrity(json.dumps(tampered_manifest), digest) is False


# =========================================================================
# 5. Gate 3 Human Approval & Ed25519 Cryptographic Attestation
# =========================================================================


def test_gate3_approval_and_ed25519_signature(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        creator_id = m11_env["creator_id"]
        reviewer_id = m11_env["reviewer_id"]
        staged_id = m11_env["staged_art_id"]

        creator = db.query(User).filter(User.id == creator_id).first()
        reviewer = db.query(User).filter(User.id == reviewer_id).first()

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=creator.id,
            name="Approval Family",
            slug=f"approval-{uuid.uuid4().hex[:6]}",
        )
        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=creator.id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        register_staged_artifact(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            staged_artifact_id=staged_id,
        )
        finalize_model_version_manifest(db, ws_id, version.id, creator.id)

        # Reviewer submits Gate 3 Approval
        approval = submit_gate3_decision(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            reviewer_user=reviewer,
            reviewer_role=WorkspaceRole.WORKSPACE_OWNER,
            decision=Gate3Decision.APPROVED,
            decision_reason="All enterprise compliance standards satisfied.",
            enforce_separation_of_duties=True,
        )
        assert approval.decision == Gate3Decision.APPROVED
        assert approval.signature_purpose == "GATE3_RELEASE_APPROVAL"
        assert approval.approval_signature is not None

        # Verify model version status and immutability
        db.refresh(version)
        assert version.status == ModelVersionStatus.APPROVED
        assert version.is_immutable is True

        # Verify signature cryptographically
        is_valid = verify_gate3_attestation(
            canonical_payload_json=approval.canonical_payload,
            signature_hex=approval.approval_signature,
            key_id=approval.signing_key_id,
        )
        assert is_valid is True


def test_separation_of_duties_enforcement(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        creator_id = m11_env["creator_id"]
        staged_id = m11_env["staged_art_id"]

        creator = db.query(User).filter(User.id == creator_id).first()

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=creator.id,
            name="Duties Family",
            slug=f"duties-{uuid.uuid4().hex[:6]}",
        )
        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=creator.id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        register_staged_artifact(db, ws_id, version.id, staged_id)
        finalize_model_version_manifest(db, ws_id, version.id, creator.id)

        # Creator attempts to approve their own release -> 403 Separation of Duties violation
        with pytest.raises(SeparationOfDutiesViolationError, match="Separation of duties violation"):
            submit_gate3_decision(
                db=db,
                workspace_id=ws_id,
                model_version_id=version.id,
                reviewer_user=creator,
                reviewer_role=WorkspaceRole.WORKSPACE_OWNER,
                decision=Gate3Decision.APPROVED,
                enforce_separation_of_duties=True,
            )


def test_signature_purpose_strict_separation():
    fake_gate1_payload = {
        "approval_id": "fake-gate1",
        "schema_version": "gate3-2026-11-09",
        "signature_purpose": "GATE1_DATA_PROTECTION",  # Gate 1 purpose
    }
    with pytest.raises(SignaturePurposeMismatchError, match="Invalid signature purpose"):
        verify_gate3_attestation(
            canonical_payload_json=json.dumps(fake_gate1_payload),
            signature_hex="dummy_sig",
            key_id="mizan-platform-dev-01",
        )


def test_immutability_after_gate3_approval(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        creator_id = m11_env["creator_id"]
        reviewer_id = m11_env["reviewer_id"]
        staged_id = m11_env["staged_art_id"]

        creator = db.query(User).filter(User.id == creator_id).first()
        reviewer = db.query(User).filter(User.id == reviewer_id).first()

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=creator.id,
            name="Immutable Family",
            slug=f"immutable-{uuid.uuid4().hex[:6]}",
        )
        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=creator.id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        register_staged_artifact(db, ws_id, version.id, staged_id)
        finalize_model_version_manifest(db, ws_id, version.id, creator.id)

        submit_gate3_decision(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            reviewer_user=reviewer,
            reviewer_role=WorkspaceRole.WORKSPACE_OWNER,
            decision=Gate3Decision.APPROVED,
            enforce_separation_of_duties=False,
        )

        # Attempt to register another artifact on approved release -> rejected
        with pytest.raises(ImmutableReleaseError):
            register_staged_artifact(db, ws_id, version.id, staged_id)

        # Attempt to finalize manifest again -> rejected
        with pytest.raises(ImmutableReleaseError):
            finalize_model_version_manifest(db, ws_id, version.id, creator.id)


def test_gate3_revocation_workflow(m11_env):
    with Session(engine) as db:
        ws_id = m11_env["ws_a_id"]
        org_id = m11_env["org_id"]
        creator_id = m11_env["creator_id"]
        reviewer_id = m11_env["reviewer_id"]
        staged_id = m11_env["staged_art_id"]

        creator = db.query(User).filter(User.id == creator_id).first()
        reviewer = db.query(User).filter(User.id == reviewer_id).first()

        family = create_model_family(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=creator.id,
            name="Revocation Family",
            slug=f"revoke-{uuid.uuid4().hex[:6]}",
        )
        version = create_model_version(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            family_id=family.id,
            user_id=creator.id,
            version_tag="v1.0.0",
            source_model_key=m11_env["model_key"],
            source_model_revision=m11_env["immutable_revision"],
            recipe_key=m11_env["recipe_key"],
        )
        register_staged_artifact(db, ws_id, version.id, staged_id)
        finalize_model_version_manifest(db, ws_id, version.id, creator.id)

        submit_gate3_decision(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            reviewer_user=reviewer,
            reviewer_role=WorkspaceRole.WORKSPACE_OWNER,
            decision=Gate3Decision.APPROVED,
            enforce_separation_of_duties=False,
        )

        # Revoke the approved release
        revocation = revoke_model_release(
            db=db,
            workspace_id=ws_id,
            model_version_id=version.id,
            revoking_user=reviewer,
            revoking_role=WorkspaceRole.WORKSPACE_OWNER,
            revocation_reason="Critical vulnerability discovered in upstream base model tokenizer.",
        )
        assert revocation.id is not None
        assert revocation.revocation_reason == "Critical vulnerability discovered in upstream base model tokenizer."

        db.refresh(version)
        assert version.status == ModelVersionStatus.REVOKED
        assert version.is_immutable is True


# =========================================================================
# 6. Tenant Isolation Tests
# =========================================================================


def test_cross_workspace_tenant_isolation(m11_env):
    with Session(engine) as db:
        ws_a_id = m11_env["ws_a_id"]
        ws_b_id = m11_env["ws_b_id"]
        org_id = m11_env["org_id"]
        creator_id = m11_env["creator_id"]

        family = create_model_family(
            db=db,
            workspace_id=ws_a_id,
            organization_id=org_id,
            user_id=creator_id,
            name="Tenant A Family",
            slug=f"tenant-a-{uuid.uuid4().hex[:6]}",
        )

        # Workspace B queries Workspace A's family -> 404
        with pytest.raises(ReleaseNotFoundError):
            get_model_family(db, workspace_id=ws_b_id, family_id=family.id)

        # Workspace B list should not include Workspace A's family
        ws_b_families = list_model_families(db, workspace_id=ws_b_id)
        assert all(f.id != family.id for f in ws_b_families)


# =========================================================================
# 7. End-to-End API Endpoints Test
# =========================================================================


def test_artifact_registry_and_gate3_api_end_to_end(m11_env):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.modules.auth.services import session_service

    client = TestClient(app)
    ws_id = m11_env["ws_a_id"]
    reviewer_id = m11_env["reviewer_id"]
    staged_id = m11_env["staged_art_id"]

    with Session(engine) as db:
        session = session_service.create_session(db, user_id=reviewer_id)
        db.commit()

    client.cookies.set("mizan_session", session.session_token)
    headers = {"X-CSRF-Token": session.csrf_token}

    # 1. Create Model Family
    f_slug = f"api-family-{uuid.uuid4().hex[:6]}"
    resp_f = client.post(
        f"/api/v1/workspaces/{ws_id}/artifact-registry/families",
        json={"name": "API Test Family", "slug": f_slug, "task_type": "TEXT_GENERATION"},
        headers=headers,
    )
    assert resp_f.status_code == 201
    family_data = resp_f.json()
    family_id = family_data["id"]

    # 2. List Families
    resp_list = client.get(f"/api/v1/workspaces/{ws_id}/artifact-registry/families")
    assert resp_list.status_code == 200
    assert any(f["id"] == family_id for f in resp_list.json())

    # 3. Create Model Version
    resp_v = client.post(
        f"/api/v1/workspaces/{ws_id}/artifact-registry/families/{family_id}/versions",
        json={
            "version_tag": "v1.0.0",
            "source_model_key": m11_env["model_key"],
            "source_model_revision": m11_env["immutable_revision"],
            "recipe_key": m11_env["recipe_key"],
            "base_evaluation_score": 0.80,
            "final_evaluation_score": 0.88,
        },
        headers=headers,
    )
    assert resp_v.status_code == 201
    version_id = resp_v.json()["id"]

    # 4. Register Staged Artifact
    resp_reg = client.post(
        f"/api/v1/workspaces/{ws_id}/artifact-registry/versions/{version_id}/register-staged-artifact",
        json={"staged_artifact_id": staged_id, "is_primary_weights": True},
        headers=headers,
    )
    assert resp_reg.status_code == 201

    # 5. Finalize Manifest
    resp_fin = client.post(
        f"/api/v1/workspaces/{ws_id}/artifact-registry/versions/{version_id}/finalize-manifest",
        headers=headers,
    )
    assert resp_fin.status_code == 200
    assert resp_fin.json()["status"] == "PENDING_REVIEW"
    manifest_digest = resp_fin.json()["release_manifest_digest"]
    assert len(manifest_digest) == 64

    # 6. Submit Gate 3 Decision (APPROVED)
    resp_decide = client.post(
        f"/api/v1/workspaces/{ws_id}/gate3/approvals/{version_id}/decide",
        json={"decision": "APPROVED", "decision_reason": "API verified approval", "enforce_separation_of_duties": False},
        headers=headers,
    )
    assert resp_decide.status_code == 200
    assert resp_decide.json()["decision"] == "APPROVED"

    # 7. Verify Signature Endpoint
    resp_sig = client.get(f"/api/v1/workspaces/{ws_id}/gate3/approvals/{version_id}/verify-signature")
    assert resp_sig.status_code == 200
    assert resp_sig.json()["is_valid"] is True
    assert resp_sig.json()["signature_purpose"] == "GATE3_RELEASE_APPROVAL"

    # 8. Revoke Release
    resp_rev = client.post(
        f"/api/v1/workspaces/{ws_id}/gate3/approvals/{version_id}/revoke",
        json={"revocation_reason": "API test revocation validation"},
        headers=headers,
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["revocation_reason"] == "API test revocation validation"
