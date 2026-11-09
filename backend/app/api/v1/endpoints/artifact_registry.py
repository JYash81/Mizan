"""REST API endpoints for Milestone 11 Artifact Registry & Model Release Management."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import Workspace
from app.modules.artifact_registry.exceptions import ArtifactRegistryError
from app.modules.artifact_registry.registry_service import (
    create_model_family,
    create_model_version,
    finalize_model_version_manifest,
    get_model_family,
    get_model_version,
    list_model_families,
    register_staged_artifact,
)
from app.modules.artifact_registry.schemas import (
    FinalizeManifestResponse,
    ModelFamilyCreateRequest,
    ModelFamilyResponse,
    ModelVersionCreateRequest,
    ModelVersionDetailResponse,
    ModelVersionResponse,
    RegisteredArtifactResponse,
    RegisterStagedArtifactRequest,
)
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission

router = APIRouter(tags=["Artifact Registry & Release Management"])


def _verify_workspace_access(db: Session, workspace_id: str) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


# =========================================================================
# Model Families
# =========================================================================


@router.get(
    "/workspaces/{workspace_id}/artifact-registry/families",
    response_model=list[ModelFamilyResponse],
    dependencies=[Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_READ))],
)
def list_families_endpoint(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ModelFamilyResponse]:
    _verify_workspace_access(db, workspace_id)
    families = list_model_families(db, workspace_id)
    return [ModelFamilyResponse.model_validate(f) for f in families]


@router.post(
    "/workspaces/{workspace_id}/artifact-registry/families",
    response_model=ModelFamilyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_CREATE)),
    ],
)
def create_family_endpoint(
    workspace_id: str,
    payload: ModelFamilyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ModelFamilyResponse:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        family = create_model_family(
            db=db,
            workspace_id=workspace_id,
            organization_id=ws.organization_id,
            user_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            task_type=payload.task_type,
        )
        return ModelFamilyResponse.model_validate(family)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/workspaces/{workspace_id}/artifact-registry/families/{family_id}",
    response_model=ModelFamilyResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_READ))],
)
def get_family_endpoint(
    workspace_id: str,
    family_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ModelFamilyResponse:
    _verify_workspace_access(db, workspace_id)
    try:
        family = get_model_family(db, workspace_id, family_id)
        return ModelFamilyResponse.model_validate(family)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =========================================================================
# Model Versions
# =========================================================================


@router.post(
    "/workspaces/{workspace_id}/artifact-registry/families/{family_id}/versions",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_CREATE)),
    ],
)
def create_version_endpoint(
    workspace_id: str,
    family_id: str,
    payload: ModelVersionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ModelVersionResponse:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        version = create_model_version(
            db=db,
            workspace_id=workspace_id,
            organization_id=ws.organization_id,
            family_id=family_id,
            user_id=current_user.id,
            version_tag=payload.version_tag,
            description=payload.description,
            build_run_id=payload.build_run_id,
            source_model_key=payload.source_model_key,
            source_model_revision=payload.source_model_revision,
            recipe_key=payload.recipe_key,
            dataset_id=payload.dataset_id,
            dataset_version_id=payload.dataset_version_id,
            dataset_version_digest=payload.dataset_version_digest,
            gate1_approval_id=payload.gate1_approval_id,
            evaluation_run_id=payload.evaluation_run_id,
            base_evaluation_score=payload.base_evaluation_score,
            final_evaluation_score=payload.final_evaluation_score,
            min_ram_mb=payload.min_ram_mb,
            min_vram_mb=payload.min_vram_mb,
            target_hardware_key=payload.target_hardware_key,
        )
        return ModelVersionResponse.model_validate(version)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/workspaces/{workspace_id}/artifact-registry/versions/{version_id}",
    response_model=ModelVersionDetailResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_READ))],
)
def get_version_endpoint(
    workspace_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ModelVersionDetailResponse:
    _verify_workspace_access(db, workspace_id)
    try:
        version = get_model_version(db, workspace_id, version_id)
        release_manifest = None
        if version.release_manifest_json:
            try:
                release_manifest = json.loads(version.release_manifest_json)
            except Exception:
                release_manifest = {}

        return ModelVersionDetailResponse(
            id=version.id,
            family_id=version.family_id,
            version_tag=version.version_tag,
            description=version.description,
            status=version.status.value,
            source_model_key=version.source_model_key,
            source_model_revision=version.source_model_revision,
            recipe_key=version.recipe_key,
            build_run_id=version.build_run_id,
            dataset_id=version.dataset_id,
            dataset_version_id=version.dataset_version_id,
            gate1_approval_id=version.gate1_approval_id,
            base_evaluation_score=version.base_evaluation_score,
            final_evaluation_score=version.final_evaluation_score,
            quality_delta=version.quality_delta,
            min_ram_mb=version.min_ram_mb,
            min_vram_mb=version.min_vram_mb,
            target_hardware_key=version.target_hardware_key,
            release_manifest_digest=version.release_manifest_digest,
            created_by=version.created_by,
            created_at=version.created_at,
            updated_at=version.updated_at,
            is_immutable=version.is_immutable,
            artifacts=[RegisteredArtifactResponse.model_validate(a) for a in version.artifacts],
            gate3_approval=version.gate3_approval,
            revocations=version.revocations,
            release_events=version.release_events,
            release_manifest=release_manifest,
            provenance_summary=version.provenance_summary,
        )
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# =========================================================================
# Artifact Promotion & Manifest Finalization
# =========================================================================


@router.post(
    "/workspaces/{workspace_id}/artifact-registry/versions/{version_id}/register-staged-artifact",
    response_model=RegisteredArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_CREATE)),
    ],
)
def register_staged_artifact_endpoint(
    workspace_id: str,
    version_id: str,
    payload: RegisterStagedArtifactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RegisteredArtifactResponse:
    _verify_workspace_access(db, workspace_id)
    try:
        registered = register_staged_artifact(
            db=db,
            workspace_id=workspace_id,
            model_version_id=version_id,
            staged_artifact_id=payload.staged_artifact_id,
            is_primary_weights=payload.is_primary_weights,
        )
        return RegisteredArtifactResponse.model_validate(registered)
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/workspaces/{workspace_id}/artifact-registry/versions/{version_id}/finalize-manifest",
    response_model=FinalizeManifestResponse,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.ARTIFACT_REGISTRY_FINALIZE)),
    ],
)
def finalize_manifest_endpoint(
    workspace_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinalizeManifestResponse:
    _verify_workspace_access(db, workspace_id)
    try:
        version, digest = finalize_model_version_manifest(
            db=db,
            workspace_id=workspace_id,
            model_version_id=version_id,
            user_id=current_user.id,
        )
        return FinalizeManifestResponse(
            version_id=version.id,
            status=version.status.value,
            release_manifest_digest=digest,
            artifact_count=len(version.artifacts),
            provenance_summary=version.provenance_summary,
        )
    except ArtifactRegistryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
