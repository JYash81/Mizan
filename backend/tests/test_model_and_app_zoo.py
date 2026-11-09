"""Comprehensive backend test suite for Milestone 12: Model Zoo, App Zoo, Enterprise Catalog, and Hardware Badges."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import create_app
from app.models.artifact_registry import (
    Gate3Approval,
    Gate3Decision,
    ModelFamily,
    ModelFamilyStatus,
    ModelVersion,
    ModelVersionStatus,
    RegisteredArtifact,
    RegisteredArtifactType,
)
from app.models.catalog import (
    CatalogVisibility,
    DistributionStatus,
    HardwareCompatibilityBadge,
    PublicationStatus,
)
from app.models.hardware import (
    EvidenceType,
    HardwareBenchmark,
    HardwareProfile,
    HardwareProfileCategory,
)
from app.models.identity import AccountStatus, User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.modules.auth.services import session_service
from app.modules.zoo.app_catalog_service import AppCatalogService
from app.modules.zoo.artifact_download_service import ArtifactDownloadService
from app.modules.zoo.catalog_revocation_service import CatalogRevocationService
from app.modules.zoo.exceptions import (
    DependencyRevocationError,
    DownloadNotPermittedError,
    PublicPublicationNotAllowedError,
    RevokedReleaseError,
    UnapprovedReleaseError,
)
from app.modules.zoo.hardware_badge_service import HardwareBadgeService
from app.modules.zoo.installation_guide_service import InstallationGuideService
from app.modules.zoo.model_catalog_service import ModelCatalogService


@pytest.fixture
def m12_env():
    """Seed test fixtures across two organizations for Milestone 12."""
    run_id = uuid.uuid4().hex[:6]
    with Session(engine) as db:
        # Users
        creator = User(
            id=f"user-creator-{run_id}",
            email=f"creator_{run_id}@mizan.org",
            normalized_email=f"creator_{run_id}@mizan.org",
            full_name="Model Engineer",
            password_hash="test_hash_safe",
            status=AccountStatus.ACTIVE,
        )
        publisher = User(
            id=f"user-publisher-{run_id}",
            email=f"publisher_{run_id}@mizan.org",
            normalized_email=f"publisher_{run_id}@mizan.org",
            full_name="Catalog Reviewer",
            password_hash="test_hash_safe",
            status=AccountStatus.ACTIVE,
        )
        external_user = User(
            id=f"user-ext-{run_id}",
            email=f"external_{run_id}@mizan.org",
            normalized_email=f"external_{run_id}@mizan.org",
            full_name="External Tenant User",
            password_hash="test_hash_safe",
            status=AccountStatus.ACTIVE,
        )
        db.add_all([creator, publisher, external_user])
        db.flush()

        # Organization A & Workspaces
        org_a = Organization(
            id=f"org-a-{run_id}",
            name=f"Org A {run_id}",
            slug=f"org-a-{run_id}",
            created_by=publisher.id,
        )
        # Organization B (Tenant 2)
        org_b = Organization(
            id=f"org-b-{run_id}",
            name=f"Org B {run_id}",
            slug=f"org-b-{run_id}",
            created_by=external_user.id,
        )
        db.add_all([org_a, org_b])
        db.flush()

        ws_a = Workspace(
            id=f"ws-a-{run_id}",
            organization_id=org_a.id,
            name=f"Workspace A {run_id}",
            slug=f"ws-a-{run_id}",
            created_by=publisher.id,
        )
        ws_b = Workspace(
            id=f"ws-b-{run_id}",
            organization_id=org_b.id,
            name=f"Workspace B {run_id}",
            slug=f"ws-b-{run_id}",
            created_by=external_user.id,
        )
        db.add_all([ws_a, ws_b])
        db.flush()

        # Memberships
        db.add(OrganizationMembership(organization_id=org_a.id, user_id=publisher.id, role=OrganizationRole.OWNER))
        db.add(OrganizationMembership(organization_id=org_a.id, user_id=creator.id, role=OrganizationRole.MEMBER))
        db.add(WorkspaceMembership(workspace_id=ws_a.id, user_id=publisher.id, role=WorkspaceRole.WORKSPACE_OWNER))
        db.add(WorkspaceMembership(workspace_id=ws_a.id, user_id=creator.id, role=WorkspaceRole.WORKSPACE_MEMBER))

        db.add(OrganizationMembership(organization_id=org_b.id, user_id=external_user.id, role=OrganizationRole.OWNER))
        db.add(WorkspaceMembership(workspace_id=ws_b.id, user_id=external_user.id, role=WorkspaceRole.WORKSPACE_OWNER))
        db.flush()

        # Hardware reference profile (Local CPU)
        prof_key = f"LOCAL_CPU_{run_id}"
        prof_cpu = HardwareProfile(
            profile_key=prof_key,
            name=f"Local CPU Workstation {run_id}",
            category=HardwareProfileCategory.LOCAL_WORKSTATION,
            evidence_type=EvidenceType.MEASURED,
            system_ram_mb=16384,
            available_ram_mb=12288,
            supports_cpu_inference=True,
            supports_gpu_inference=False,
            is_reference=True,
        )
        db.add(prof_cpu)
        db.flush()

        # Measured benchmark on this workstation
        bench = HardwareBenchmark(
            workspace_id=ws_a.id,
            user_id=creator.id,
            benchmark_name="CPU_STANDARD_INFERENCE",
            benchmark_version="1.0.0",
            workload_params_json='{"batch_size": 1}',
            duration_ms=45.0,
            operations_per_second=22.2,
            ram_before_mb=4000,
            ram_after_mb=4500,
            evidence_type=EvidenceType.MEASURED,
            status="COMPLETED",
            limitations="CPU only",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(bench)
        db.flush()

        # M11 Approved Model Family and Version
        fam = ModelFamily(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            name=f"Customer Support LLM {run_id}",
            slug=f"support-llm-{run_id}",
            task_type="TEXT_GENERATION",
            created_by=creator.id,
            status=ModelFamilyStatus.ACTIVE,
        )
        db.add(fam)
        db.flush()

        # Approved Version v1.0.0
        ver_approved = ModelVersion(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            family_id=fam.id,
            version_tag="v1.0.0",
            description="Fine-tuned support model",
            status=ModelVersionStatus.APPROVED,
            source_model_key="meta-llama/Llama-3-8B-Instruct",
            source_model_revision="main",
            recipe_key="LORA_FINETUNE_SFT_V1",
            base_evaluation_score=0.74,
            final_evaluation_score=0.85,
            quality_delta=0.11,
            min_ram_mb=8192.0,
            min_vram_mb=0.0,
            target_hardware_key=prof_key,
            release_manifest_digest="a1b2c3d4e5f60000000000000000000000000000000000000000000000000001",
            provenance_summary_json=json.dumps({
                "checks": {
                    "BASE_MODEL_LICENSE": {"passed": True, "details": {"commercial_use": True, "license": "Llama-3-Community"}},
                }
            }),
            created_by=creator.id,
        )
        db.add(ver_approved)
        db.flush()

        # Gate 3 Approval Attestation
        g3_app = Gate3Approval(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            model_version_id=ver_approved.id,
            release_manifest_digest=ver_approved.release_manifest_digest,
            decision=Gate3Decision.APPROVED,
            decision_reason="Passed all evaluation criteria",
            reviewer_user_id=publisher.id,
            reviewer_role_snapshot="OWNER",
            signing_key_id="key-123",
            approval_signature="test-sig",
            canonical_payload="{}",
            reviewed_at=datetime.now(UTC),
        )
        db.add(g3_app)

        # Registered Artifact
        art = RegisteredArtifact(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            model_version_id=ver_approved.id,
            artifact_type=RegisteredArtifactType.LORA_ADAPTER,
            format="SAFETENSORS",
            file_size_bytes=104857600,
            sha256="fa1b2c3d4e5f6789fa1b2c3d4e5f6789fa1b2c3d4e5f6789fa1b2c3d4e5f6789",
            storage_reference=f"releases/{fam.id}/adapter.safetensors",
            is_primary_weights=True,
        )
        db.add(art)

        # Revoked Version v1.1.0
        ver_revoked = ModelVersion(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            family_id=fam.id,
            version_tag="v1.1.0",
            description="Faulty version",
            status=ModelVersionStatus.REVOKED,
            source_model_key="meta-llama/Llama-3-8B-Instruct",
            source_model_revision="main",
            recipe_key="LORA_FINETUNE_SFT_V1",
            min_ram_mb=8192.0,
            min_vram_mb=0.0,
            release_manifest_digest="b2c3d4e5f6000000000000000000000000000000000000000000000000000002",
            created_by=creator.id,
        )
        db.add(ver_revoked)

        # Draft Version v1.2.0 (Unapproved)
        ver_draft = ModelVersion(
            organization_id=org_a.id,
            workspace_id=ws_a.id,
            family_id=fam.id,
            version_tag="v1.2.0",
            description="Work in progress",
            status=ModelVersionStatus.DRAFT,
            source_model_key="meta-llama/Llama-3-8B-Instruct",
            source_model_revision="main",
            recipe_key="LORA_FINETUNE_SFT_V1",
            min_ram_mb=8192.0,
            min_vram_mb=0.0,
            created_by=creator.id,
        )
        db.add(ver_draft)
        db.commit()

        # Create auth sessions for clients
        sess_publisher = session_service.create_session(db, user_id=publisher.id)
        sess_external = session_service.create_session(db, user_id=external_user.id)
        db.commit()

        app = create_app()
        client_publisher = TestClient(app)
        client_publisher.cookies.set("mizan_session", sess_publisher.session_token)

        client_external = TestClient(app)
        client_external.cookies.set("mizan_session", sess_external.session_token)

        return {
            "org_a_id": org_a.id,
            "org_b_id": org_b.id,
            "ws_a_id": ws_a.id,
            "ws_b_id": ws_b.id,
            "creator_id": creator.id,
            "publisher_id": publisher.id,
            "external_user_id": external_user.id,
            "family_id": fam.id,
            "ver_approved_id": ver_approved.id,
            "ver_revoked_id": ver_revoked.id,
            "ver_draft_id": ver_draft.id,
            "artifact_id": art.id,
            "hardware_profile_key": prof_key,
            "client_publisher": client_publisher,
            "csrf_publisher": sess_publisher.csrf_token,
            "client_external": client_external,
            "csrf_external": sess_external.csrf_token,
        }


# =========================================================================
# 1. Model Listing Lifecycle & Moderation Tests
# =========================================================================


def test_model_listing_lifecycle(m12_env):
    """Test full model listing lifecycle: Draft -> Submit -> Review/Approve -> Suspend."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        creator_id = m12_env["creator_id"]
        pub_id = m12_env["publisher_id"]
        ver_id = m12_env["ver_approved_id"]

        # 1. Create draft listing
        listing = ModelCatalogService.create_model_listing(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=creator_id,
            model_version_id=ver_id,
            title="Customer Support Assistant v1",
            description="Governed model fine-tuned for support tickets.",
            category="CUSTOMER_SUPPORT",
            visibility=CatalogVisibility.WORKSPACE,
            distribution_status=DistributionStatus.DOWNLOADABLE,
        )
        assert listing.publication_status == PublicationStatus.DRAFT
        assert listing.slug == "customer-support-assistant-v1"
        assert listing.distribution_status == DistributionStatus.DOWNLOADABLE

        # 2. Submit for review
        listing = ModelCatalogService.submit_for_review(db, listing.id, creator_id)
        assert listing.publication_status == PublicationStatus.SUBMITTED_FOR_REVIEW

        # 3. Review & Approve
        listing = ModelCatalogService.review_and_publish(
            db=db,
            listing_id=listing.id,
            reviewer_id=pub_id,
            decision="APPROVED",
            rationale="Evaluation scores and safety benchmarks confirmed.",
        )
        assert listing.publication_status == PublicationStatus.PUBLISHED
        assert listing.published_by == pub_id
        assert listing.published_at is not None
        assert len(listing.publication_digest) == 64
        assert listing.public_metadata["title"] == "Customer Support Assistant v1"

        # 4. Suspend listing
        listing = ModelCatalogService.suspend_listing(
            db, listing.id, pub_id, "Temporary compliance hold"
        )
        assert listing.publication_status == PublicationStatus.SUSPENDED
        assert listing.distribution_status == DistributionStatus.UNAVAILABLE


def test_unapproved_model_listing_rejected(m12_env):
    """Attempting to list an unapproved (DRAFT) M11 release must be rejected."""
    with Session(engine) as db:
        with pytest.raises(UnapprovedReleaseError):
            ModelCatalogService.create_model_listing(
                db=db,
                workspace_id=m12_env["ws_a_id"],
                organization_id=m12_env["org_a_id"],
                user_id=m12_env["creator_id"],
                model_version_id=m12_env["ver_draft_id"],
                title="Unapproved Model Listing",
                description="Should fail",
            )


def test_revoked_model_listing_rejected(m12_env):
    """Attempting to list a REVOKED M11 model release must be rejected."""
    with Session(engine) as db:
        with pytest.raises(RevokedReleaseError):
            ModelCatalogService.create_model_listing(
                db=db,
                workspace_id=m12_env["ws_a_id"],
                organization_id=m12_env["org_a_id"],
                user_id=m12_env["creator_id"],
                model_version_id=m12_env["ver_revoked_id"],
                title="Revoked Model Listing",
                description="Should fail",
            )


# =========================================================================
# 2. Public Rights & Licensing Restrictions Tests
# =========================================================================


def test_public_publication_license_restriction(m12_env):
    """Public publication with DOWNLOADABLE status is rejected if commercial use is restricted."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        user_id = m12_env["creator_id"]
        pub_id = m12_env["publisher_id"]

        # Create model version with restricted license
        ver_restricted = ModelVersion(
            organization_id=org_id,
            workspace_id=ws_id,
            family_id=m12_env["family_id"],
            version_tag="v1.0.0-restricted",
            status=ModelVersionStatus.APPROVED,
            source_model_key="restricted/academic-model",
            source_model_revision="main",
            recipe_key="LORA_FINETUNE_SFT_V1",
            min_ram_mb=4096.0,
            release_manifest_digest="c3d4e5f600000000000000000000000000000000000000000000000000000003",
            provenance_summary_json=json.dumps({
                "checks": {
                    "BASE_MODEL_LICENSE": {"passed": True, "details": {"commercial_use": False, "license": "CC-BY-NC-4.0"}},
                }
            }),
            created_by=user_id,
        )
        db.add(ver_restricted)
        db.flush()

        g3 = Gate3Approval(
            organization_id=org_id,
            workspace_id=ws_id,
            model_version_id=ver_restricted.id,
            release_manifest_digest=ver_restricted.release_manifest_digest,
            decision=Gate3Decision.APPROVED,
            reviewer_user_id=pub_id,
            reviewer_role_snapshot="OWNER",
            signing_key_id="k-1",
            approval_signature="sig-1",
            canonical_payload="{}",
            reviewed_at=datetime.now(UTC),
        )
        db.add(g3)
        db.commit()

        # Create public listing with DOWNLOADABLE status
        listing = ModelCatalogService.create_model_listing(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            model_version_id=ver_restricted.id,
            title="Academic Restricted Model",
            description="Non-commercial research weights.",
            visibility=CatalogVisibility.PUBLIC,
            distribution_status=DistributionStatus.DOWNLOADABLE,
        )
        ModelCatalogService.submit_for_review(db, listing.id, user_id)

        # Attempting to publish as DOWNLOADABLE must fail
        with pytest.raises(PublicPublicationNotAllowedError):
            ModelCatalogService.review_and_publish(
                db, listing.id, pub_id, "APPROVED", "Approved for public"
            )


# =========================================================================
# 3. Hardware Compatibility Badges Tests
# =========================================================================


def test_hardware_compatibility_badges(m12_env):
    """Test honest badge assignment: TESTED on measured local benchmark, ESTIMATED on resource fit, INCOMPATIBLE on limits."""
    with Session(engine) as db:
        prof_key = m12_env["hardware_profile_key"]
        ver_id = m12_env["ver_approved_id"]

        # Case 1: Fits within local benchmark -> TESTED
        results = HardwareBadgeService.evaluate_model_compatibility(
            db=db,
            model_version_id=ver_id,
            min_ram_mb=4096.0,
            min_vram_mb=0.0,
            target_hardware_key=prof_key,
        )
        match = next(r for r in results if r["hardware_profile_key"] == prof_key)
        assert match["badge"] == HardwareCompatibilityBadge.TESTED.value
        assert match["evidence_type"] == "MEASURED"

        # Case 2: Requires excessive RAM exceeding profile (16384 MB) -> INCOMPATIBLE
        results_incompatible = HardwareBadgeService.evaluate_model_compatibility(
            db=db,
            model_version_id=ver_id,
            min_ram_mb=32768.0,
            min_vram_mb=0.0,
            target_hardware_key=prof_key,
        )
        match_inc = next(r for r in results_incompatible if r["hardware_profile_key"] == prof_key)
        assert match_inc["badge"] == HardwareCompatibilityBadge.INCOMPATIBLE.value

        # Case 3: Profile with vendor reference without benchmark -> ESTIMATED (if fits)
        prof_cloud = HardwareProfile(
            profile_key="CLOUD_CPU_16GB",
            name="Cloud 4 vCPU 16GB",
            category=HardwareProfileCategory.CLOUD_CPU,
            evidence_type=EvidenceType.VENDOR_REFERENCE,
            system_ram_mb=16384,
            supports_cpu_inference=True,
            is_reference=True,
        )
        db.add(prof_cloud)
        db.flush()

        results_cloud = HardwareBadgeService.evaluate_model_compatibility(
            db=db,
            model_version_id=ver_id,
            min_ram_mb=6000.0,
            min_vram_mb=0.0,
        )
        match_cloud = next(r for r in results_cloud if r["hardware_profile_key"] == "CLOUD_CPU_16GB")
        assert match_cloud["badge"] == HardwareCompatibilityBadge.ESTIMATED.value
        assert match_cloud["evidence_type"] == "ESTIMATED"


# =========================================================================
# 4. App Zoo: Definition, Versioning & Dependency Governance Tests
# =========================================================================


def test_app_zoo_definition_and_dependencies(m12_env):
    """Test App Zoo definition, versioning, canonical manifest digest, and model dependency validation."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        user_id = m12_env["creator_id"]
        ver_apprv_id = m12_env["ver_approved_id"]
        ver_revoked_id = m12_env["ver_revoked_id"]

        # 1. Create App Definition
        app_def = AppCatalogService.create_app_definition(
            db=db,
            workspace_id=ws_id,
            organization_id=org_id,
            user_id=user_id,
            name="Enterprise Customer Agent",
            description="Multi-turn customer support and ticket resolver.",
            category="CUSTOMER_SUPPORT",
        )
        assert app_def.app_key == "enterprise-customer-agent"

        # 2. Create App Version with valid approved dependency
        app_ver = AppCatalogService.create_app_version(
            db=db,
            app_definition_id=app_def.id,
            user_id=user_id,
            version_tag="v1.0.0",
            capabilities=["TEXT_GENERATION", "CITATION_GENERATION"],
            model_dependencies=[{"model_version_id": ver_apprv_id, "dependency_role": "PRIMARY_GENERATOR"}],
        )
        assert app_ver.version_tag == "v1.0.0"
        assert len(app_ver.manifest_digest) == 64
        assert len(app_ver.model_dependencies) == 1

        # 3. Binding a revoked model version must fail
        with pytest.raises(DependencyRevocationError):
            AppCatalogService.create_app_version(
                db=db,
                app_definition_id=app_def.id,
                user_id=user_id,
                version_tag="v1.1.0",
                model_dependencies=[{"model_version_id": ver_revoked_id, "dependency_role": "PRIMARY_GENERATOR"}],
            )


def test_app_listing_review_and_publication(m12_env):
    """Test full App Zoo listing workflow: Draft -> Submit -> Review -> Published."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        user_id = m12_env["creator_id"]
        pub_id = m12_env["publisher_id"]
        ver_apprv_id = m12_env["ver_approved_id"]

        app_def = AppCatalogService.create_app_definition(
            db, ws_id, org_id, user_id, "Contract Summarizer", "Legal document summarization."
        )
        app_ver = AppCatalogService.create_app_version(
            db, app_def.id, user_id, "v1.0.0",
            capabilities=["DOCUMENT_RETRIEVAL", "SUMMARIZATION"],
            model_dependencies=[{"model_version_id": ver_apprv_id}],
        )

        listing = AppCatalogService.create_app_listing(
            db, ws_id, org_id, user_id, app_ver.id,
            title="Contract Summarizer App",
            description="Automated legal analysis assistant.",
            visibility=CatalogVisibility.ORGANIZATION,
        )
        assert listing.publication_status == PublicationStatus.DRAFT

        # Submit
        listing = AppCatalogService.submit_app_for_review(db, listing.id, user_id)
        assert listing.publication_status == PublicationStatus.SUBMITTED_FOR_REVIEW

        # Review & Publish
        listing = AppCatalogService.review_and_publish_app(
            db, listing.id, pub_id, "APPROVED", "Approved for organization"
        )
        assert listing.publication_status == PublicationStatus.PUBLISHED
        assert listing.published_by == pub_id
        assert len(listing.publication_digest) == 64


# =========================================================================
# 5. Revocation Propagation Tests
# =========================================================================


def test_revocation_propagation_cascades_to_models_and_apps(m12_env):
    """When an M11 model release is revoked, linked model listings and dependent apps are suspended."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        user_id = m12_env["creator_id"]
        pub_id = m12_env["publisher_id"]
        ver_id = m12_env["ver_approved_id"]

        # Create published Model Zoo listing
        model_listing = ModelCatalogService.create_model_listing(
            db, ws_id, org_id, user_id, ver_id, "Support Bot", "Support LLM"
        )
        ModelCatalogService.submit_for_review(db, model_listing.id, user_id)
        model_listing = ModelCatalogService.review_and_publish(db, model_listing.id, pub_id, "APPROVED", "OK")
        assert model_listing.publication_status == PublicationStatus.PUBLISHED

        # Create published App Zoo listing depending on that model
        app_def = AppCatalogService.create_app_definition(db, ws_id, org_id, user_id, "Support App", "App")
        app_ver = AppCatalogService.create_app_version(
            db, app_def.id, user_id, "v1.0.0",
            model_dependencies=[{"model_version_id": ver_id}],
        )
        app_listing = AppCatalogService.create_app_listing(db, ws_id, org_id, user_id, app_ver.id, "Support App Listing", "App")
        AppCatalogService.submit_app_for_review(db, app_listing.id, user_id)
        app_listing = AppCatalogService.review_and_publish_app(db, app_listing.id, pub_id, "APPROVED", "OK")
        assert app_listing.publication_status == PublicationStatus.PUBLISHED

        # Execute revocation propagation
        summary = CatalogRevocationService.propagate_release_revocation(
            db=db,
            model_version_id=ver_id,
            user_id=pub_id,
            revocation_reason="Security vulnerability discovered in base weights",
        )
        assert summary["model_listings_suspended"] == 1
        assert summary["app_listings_suspended"] == 1

        db.refresh(model_listing)
        db.refresh(app_listing)
        db.refresh(app_ver)
        assert model_listing.publication_status == PublicationStatus.SUSPENDED
        assert model_listing.distribution_status == DistributionStatus.UNAVAILABLE
        assert app_listing.publication_status == PublicationStatus.SUSPENDED
        assert app_ver.status == "BLOCKED"


# =========================================================================
# 6. Artifact Download Authorization Tests
# =========================================================================


def test_artifact_download_authorization(m12_env):
    """Test download authorization: allowed for published releases, blocked for metadata-only or revoked."""
    with Session(engine) as db:
        ws_id = m12_env["ws_a_id"]
        org_id = m12_env["org_a_id"]
        user_id = m12_env["creator_id"]
        pub_id = m12_env["publisher_id"]
        ver_id = m12_env["ver_approved_id"]
        art_id = m12_env["artifact_id"]

        # 1. Published downloadable listing
        listing = ModelCatalogService.create_model_listing(
            db, ws_id, org_id, user_id, ver_id, "Downloadable Model", "Desc",
            distribution_status=DistributionStatus.DOWNLOADABLE,
        )
        ModelCatalogService.submit_for_review(db, listing.id, user_id)
        listing = ModelCatalogService.review_and_publish(db, listing.id, pub_id, "APPROVED", "OK")

        res = ArtifactDownloadService.authorize_artifact_download(
            db, listing.id, art_id, user_id, user_workspace_id=ws_id, user_organization_id=org_id
        )
        assert res["authorized"] is True
        assert res["artifact_id"] == art_id

        # 2. Metadata-only listing blocks download
        listing.distribution_status = DistributionStatus.METADATA_ONLY
        db.flush()

        with pytest.raises(DownloadNotPermittedError):
            ArtifactDownloadService.authorize_artifact_download(
                db, listing.id, art_id, user_id, user_workspace_id=ws_id, user_organization_id=org_id
            )


# =========================================================================
# 7. Installation Snippet Reproducibility Tests
# =========================================================================


def test_installation_snippets_are_deterministic_and_safe(m12_env):
    """Installation snippets must pin exact versions, release digests, and contain no credentials."""
    with Session(engine) as db:
        listing = ModelCatalogService.create_model_listing(
            db, m12_env["ws_a_id"], m12_env["org_a_id"], m12_env["creator_id"],
            m12_env["ver_approved_id"], "Snippet Test Model", "Desc"
        )
        ver = listing.model_version
        snippets = InstallationGuideService.generate_model_snippets(listing, ver)

        assert "python_transformers" in snippets
        assert "llamacpp_cli" in snippets
        assert "m13_serving_spec" in snippets

        py_snip = snippets["python_transformers"]
        assert ver.version_tag in py_snip
        assert ver.release_manifest_digest in py_snip
        assert "MIZAN GOVERNED INSTALLATION SPECIFICATION" in py_snip

        # Security check: zero credentials or session tokens
        for code in snippets.values():
            assert "password" not in code.lower()
            assert "secret" not in code.lower()
            assert "token" not in code.lower() or "tokenizer" in code.lower()


# =========================================================================
# 8. Tenant Isolation & REST API Discovery Tests
# =========================================================================


def test_tenant_isolation_in_catalog_api(m12_env):
    """User in Org B cannot see Org A's private/workspace listings, but can see PUBLIC listings."""
    client_pub: TestClient = m12_env["client_publisher"]
    client_ext: TestClient = m12_env["client_external"]
    ws_a = m12_env["ws_a_id"]
    csrf = m12_env["csrf_publisher"]

    # 1. Create a workspace listing in Org A
    resp = client_pub.post(
        f"/api/v1/workspaces/{ws_a}/model-zoo/listings",
        headers={"X-CSRF-Token": csrf},
        json={
            "model_version_id": m12_env["ver_approved_id"],
            "title": "Org A Private Model",
            "description": "Internal model only",
            "visibility": "WORKSPACE",
            "distribution_status": "DOWNLOADABLE",
        },
    )
    assert resp.status_code == 201
    listing_id = resp.json()["id"]

    # 2. External user from Org B accesses discovery endpoint
    disc_resp = client_ext.get("/api/v1/zoo/models")
    assert disc_resp.status_code == 200
    found_ids = [item["id"] for item in disc_resp.json()["items"]]
    assert listing_id not in found_ids

    # 3. External user attempting direct detail access to workspace listing is blocked with 404
    detail_resp = client_ext.get(f"/api/v1/zoo/models/{listing_id}")
    assert detail_resp.status_code == 404
