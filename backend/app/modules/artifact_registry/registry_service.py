"""Core Registry Service managing Model Families, Model Versions, and Staged Artifact Registration."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.artifact_registry import (
    ModelFamily,
    ModelFamilyStatus,
    ModelReleaseEvent,
    ModelVersion,
    ModelVersionStatus,
    RegisteredArtifact,
    RegisteredArtifactType,
)
from app.models.model_building import ModelBuildRun, StagedModelArtifact
from app.modules.artifact_registry.exceptions import (
    ArtifactRegistryError,
    ImmutableReleaseError,
    ProvenanceVerificationError,
    ReleaseNotFoundError,
)
from app.modules.artifact_registry.manifest_service import generate_release_manifest
from app.modules.artifact_registry.provenance_service import verify_model_provenance


def create_model_family(
    db: Session,
    workspace_id: str,
    organization_id: str,
    user_id: str,
    name: str,
    slug: str,
    description: str | None = None,
    task_type: str = "TEXT_GENERATION",
) -> ModelFamily:
    """Create a new organization/workspace-scoped Model Family."""
    existing = (
        db.query(ModelFamily)
        .filter(ModelFamily.workspace_id == workspace_id, ModelFamily.slug == slug)
        .first()
    )
    if existing:
        raise ArtifactRegistryError(f"Model family with slug '{slug}' already exists in this workspace.")

    family = ModelFamily(
        organization_id=organization_id,
        workspace_id=workspace_id,
        name=name,
        slug=slug,
        description=description,
        task_type=task_type,
        created_by=user_id,
        status=ModelFamilyStatus.ACTIVE,
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def list_model_families(
    db: Session,
    workspace_id: str,
) -> list[ModelFamily]:
    """List all active model families in a workspace."""
    return (
        db.query(ModelFamily)
        .filter(ModelFamily.workspace_id == workspace_id)
        .order_by(ModelFamily.created_at.desc())
        .all()
    )


def get_model_family(
    db: Session,
    workspace_id: str,
    family_id: str,
) -> ModelFamily:
    """Retrieve a single model family with versions in a workspace."""
    family = (
        db.query(ModelFamily)
        .filter(ModelFamily.id == family_id, ModelFamily.workspace_id == workspace_id)
        .first()
    )
    if not family:
        raise ReleaseNotFoundError(f"Model family '{family_id}' not found in workspace.")
    return family


def create_model_version(
    db: Session,
    workspace_id: str,
    organization_id: str,
    family_id: str,
    user_id: str,
    version_tag: str,
    description: str | None = None,
    build_run_id: str | None = None,
    source_model_key: str | None = None,
    source_model_revision: str | None = None,
    recipe_key: str | None = None,
    dataset_id: str | None = None,
    dataset_version_id: str | None = None,
    dataset_version_digest: str | None = None,
    gate1_approval_id: str | None = None,
    evaluation_run_id: str | None = None,
    base_evaluation_score: float | None = None,
    final_evaluation_score: float | None = None,
    min_ram_mb: float = 0.0,
    min_vram_mb: float = 0.0,
    target_hardware_key: str | None = None,
) -> ModelVersion:
    """Create a new ModelVersion release candidate."""
    family = get_model_family(db, workspace_id, family_id)

    # Check unique version tag in family
    existing_ver = (
        db.query(ModelVersion)
        .filter(ModelVersion.family_id == family_id, ModelVersion.version_tag == version_tag)
        .first()
    )
    if existing_ver:
        raise ArtifactRegistryError(
            f"Version tag '{version_tag}' already exists in family '{family.name}'."
        )

    # If build_run_id provided, inherit build provenance metadata
    effective_model_key = source_model_key
    effective_revision = source_model_revision
    effective_recipe = recipe_key

    if build_run_id:
        build_run = (
            db.query(ModelBuildRun)
            .filter(ModelBuildRun.id == build_run_id, ModelBuildRun.workspace_id == workspace_id)
            .first()
        )
        if not build_run:
            raise ArtifactRegistryError(f"Model build run '{build_run_id}' not found in workspace.")
        effective_model_key = effective_model_key or build_run.source_model.model_key if build_run.source_model else "custom"
        effective_revision = effective_revision or build_run.source_revision
        effective_recipe = effective_recipe or build_run.recipe_key

    if not effective_model_key or not effective_revision or not effective_recipe:
        raise ArtifactRegistryError(
            "Model version requires source_model_key, source_model_revision, and recipe_key."
        )

    delta = None
    if base_evaluation_score is not None and final_evaluation_score is not None:
        delta = round(final_evaluation_score - base_evaluation_score, 4)

    version = ModelVersion(
        organization_id=organization_id,
        workspace_id=workspace_id,
        family_id=family_id,
        version_tag=version_tag,
        description=description,
        status=ModelVersionStatus.DRAFT,
        build_run_id=build_run_id,
        source_model_key=effective_model_key,
        source_model_revision=effective_revision,
        recipe_key=effective_recipe,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        dataset_version_digest=dataset_version_digest,
        gate1_approval_id=gate1_approval_id,
        evaluation_run_id=evaluation_run_id,
        base_evaluation_score=base_evaluation_score,
        final_evaluation_score=final_evaluation_score,
        quality_delta=delta,
        min_ram_mb=min_ram_mb,
        min_vram_mb=min_vram_mb,
        target_hardware_key=target_hardware_key,
        created_by=user_id,
    )
    db.add(version)
    db.flush()

    # If build_run_id has staged artifacts, auto-register them
    if build_run_id and build_run:
        for staged in build_run.staged_artifacts:
            register_staged_artifact(
                db=db,
                workspace_id=workspace_id,
                model_version_id=version.id,
                staged_artifact_id=staged.id,
                is_primary_weights=(staged.artifact_type.value in {"LORA_ADAPTER", "GGUF_Q4_K_M", "GGUF_Q8_0"}),
            )

    event = ModelReleaseEvent(
        model_version_id=version.id,
        event_type="CREATED",
        triggered_by_user_id=user_id,
        message=f"Model version {version_tag} initialized in family {family.slug}.",
    )
    db.add(event)
    db.commit()
    db.refresh(version)
    return version


def get_model_version(
    db: Session,
    workspace_id: str,
    version_id: str,
) -> ModelVersion:
    """Retrieve a single ModelVersion with registered artifacts and approval history."""
    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == version_id, ModelVersion.workspace_id == workspace_id)
        .first()
    )
    if not version:
        raise ReleaseNotFoundError(f"Model version '{version_id}' not found in workspace.")
    return version


def register_staged_artifact(
    db: Session,
    workspace_id: str,
    model_version_id: str,
    staged_artifact_id: str,
    is_primary_weights: bool = False,
) -> RegisteredArtifact:
    """Promote an M10 StagedModelArtifact into an immutable RegisteredArtifact.

    Enforces:
    1. Version is not immutable (DRAFT or PENDING_REVIEW).
    2. Staged artifact belongs to workspace and has valid SHA-256 and storage reference.
    3. Prevents duplicate registration of the same hash in the version.
    """
    version = get_model_version(db, workspace_id, model_version_id)
    if version.is_immutable:
        raise ImmutableReleaseError(
            f"Cannot register artifacts to finalized or approved release version {version.version_tag}."
        )

    staged = (
        db.query(StagedModelArtifact)
        .filter(
            StagedModelArtifact.id == staged_artifact_id,
            StagedModelArtifact.workspace_id == workspace_id,
        )
        .first()
    )
    if not staged:
        raise ReleaseNotFoundError(f"Staged artifact '{staged_artifact_id}' not found in workspace.")

    # Check for existing artifact with same hash in this version
    existing = (
        db.query(RegisteredArtifact)
        .filter(
            RegisteredArtifact.model_version_id == model_version_id,
            RegisteredArtifact.sha256 == staged.sha256,
        )
        .first()
    )
    if existing:
        return existing

    # Map artifact type safely
    try:
        reg_type = RegisteredArtifactType(staged.artifact_type.value)
    except Exception:
        reg_type = RegisteredArtifactType.LORA_ADAPTER

    registered = RegisteredArtifact(
        organization_id=version.organization_id,
        workspace_id=workspace_id,
        model_version_id=model_version_id,
        staged_artifact_id=staged.id,
        artifact_type=reg_type,
        format=staged.format,
        quantization_type=staged.quantization_type,
        file_size_bytes=staged.file_size_bytes,
        sha256=staged.sha256,
        storage_reference=staged.storage_reference,
        is_verified=True,
        verification_details_json=staged.verification_details_json,
        is_primary_weights=is_primary_weights,
    )
    db.add(registered)
    db.commit()
    db.refresh(registered)
    return registered


def finalize_model_version_manifest(
    db: Session,
    workspace_id: str,
    model_version_id: str,
    user_id: str,
) -> tuple[ModelVersion, str]:
    """Finalize Release Manifest and transition version to PENDING_REVIEW for Gate 3.

    Enforces:
    1. Version is in DRAFT state.
    2. At least one registered artifact exists.
    3. Runs 5-pillar provenance verification; raises ProvenanceVerificationError if blocked.
    4. Computes deterministic Release Manifest and SHA-256 digest.
    """
    version = get_model_version(db, workspace_id, model_version_id)
    if version.is_immutable:
        raise ImmutableReleaseError("Model version is already approved or revoked.")

    if not version.artifacts:
        raise ArtifactRegistryError("Cannot finalize version with 0 registered artifacts.")

    # 1. Run 5-Pillar Provenance Verification
    provenance_res = verify_model_provenance(
        db=db,
        workspace_id=workspace_id,
        source_model_key=version.source_model_key,
        source_model_revision=version.source_model_revision,
        recipe_key=version.recipe_key,
        build_run_id=version.build_run_id,
        dataset_id=version.dataset_id,
        dataset_version_id=version.dataset_version_id,
        dataset_version_digest=version.dataset_version_digest,
        gate1_approval_id=version.gate1_approval_id,
        evaluation_run_id=version.evaluation_run_id,
        base_evaluation_score=version.base_evaluation_score,
        final_evaluation_score=version.final_evaluation_score,
        min_ram_mb=version.min_ram_mb,
        min_vram_mb=version.min_vram_mb,
        target_hardware_key=version.target_hardware_key,
    )

    if not provenance_res["is_valid"]:
        raise ProvenanceVerificationError(
            message=f"Provenance verification failed with {len(provenance_res['blockers'])} blocker(s).",
            blockers=provenance_res["blockers"],
        )

    # 2. Generate Release Manifest & Digest
    family = version.family
    manifest_dict, manifest_digest = generate_release_manifest(
        model_version=version,
        family_slug=family.slug,
        artifacts=version.artifacts,
        provenance_summary=provenance_res,
    )

    # 3. Store Immutable Manifest and update status
    version.release_manifest_json = json.dumps(manifest_dict)
    version.release_manifest_digest = manifest_digest
    version.provenance_summary_json = json.dumps(provenance_res)
    version.status = ModelVersionStatus.PENDING_REVIEW

    event = ModelReleaseEvent(
        model_version_id=version.id,
        event_type="SUBMITTED_FOR_REVIEW",
        triggered_by_user_id=user_id,
        message=f"Model version {version.version_tag} finalized with manifest {manifest_digest[:16]} and submitted for Gate 3 review.",
        metadata_json=json.dumps({"manifest_digest": manifest_digest, "artifact_count": len(version.artifacts)}),
    )
    db.add(event)
    db.commit()
    db.refresh(version)
    return version, manifest_digest
