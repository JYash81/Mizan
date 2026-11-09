"""Dataset management API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.datasets.schemas import (
    DatasetCreateRequest,
    DatasetResponse,
    DatasetUpdateRequest,
    DatasetVersionCreateRequest,
    DatasetVersionResponse,
)
from app.modules.datasets.services import dataset_service

router = APIRouter(tags=["Datasets"])


@router.post(
    "/workspaces/{workspace_id}/datasets",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_dataset(
    workspace_id: str,
    payload: DatasetCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_CREATE)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        ds, ver = dataset_service.create_dataset(
            db=db,
            workspace_id=ws.id,
            creator_id=current_user.id,
            name=payload.name,
            description=payload.description,
            slug=payload.slug,
        )
        return {
            "dataset": DatasetResponse.model_validate(ds),
            "version": DatasetVersionResponse.model_validate(ver),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/workspaces/{workspace_id}/datasets",
    status_code=status.HTTP_200_OK,
)
def list_datasets(
    workspace_id: str,
    include_archived: bool = False,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    datasets = dataset_service.list_datasets(db, ws.id, include_archived=include_archived)

    # Attach active version to each dataset for UI convenience
    results = []
    for ds in datasets:
        ds_resp = DatasetResponse.model_validate(ds)
        versions = dataset_service.list_dataset_versions(db, ds.id)
        if versions:
            ds_resp.active_version = DatasetVersionResponse.model_validate(versions[0])
        results.append(ds_resp)

    return {"datasets": results}


@router.get(
    "/workspaces/{workspace_id}/datasets/{dataset_id}",
    status_code=status.HTTP_200_OK,
)
def get_dataset(
    workspace_id: str,
    dataset_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    ds = dataset_service.get_dataset(db, ws.id, dataset_id)
    if ds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    ds_resp = DatasetResponse.model_validate(ds)
    versions = dataset_service.list_dataset_versions(db, ds.id)
    if versions:
        ds_resp.active_version = DatasetVersionResponse.model_validate(versions[0])

    return {"dataset": ds_resp}


@router.patch(
    "/workspaces/{workspace_id}/datasets/{dataset_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def update_dataset(
    workspace_id: str,
    dataset_id: str,
    payload: DatasetUpdateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_UPDATE)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        ds = dataset_service.update_dataset(
            db=db,
            workspace_id=ws.id,
            dataset_id=dataset_id,
            name=payload.name,
            description=payload.description,
        )
        return {"dataset": DatasetResponse.model_validate(ds)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/workspaces/{workspace_id}/datasets/{dataset_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def archive_dataset(
    workspace_id: str,
    dataset_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_DELETE)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        ds = dataset_service.archive_dataset(db=db, workspace_id=ws.id, dataset_id=dataset_id)
        return {"dataset": DatasetResponse.model_validate(ds)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/workspaces/{workspace_id}/datasets/{dataset_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_dataset_version(
    workspace_id: str,
    dataset_id: str,
    payload: DatasetVersionCreateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_CREATE)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        ver = dataset_service.create_dataset_version(
            db=db,
            workspace_id=ws.id,
            dataset_id=dataset_id,
            name=payload.name,
            description=payload.description,
        )
        return {"version": DatasetVersionResponse.model_validate(ver)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/workspaces/{workspace_id}/datasets/{dataset_id}/versions",
    status_code=status.HTTP_200_OK,
)
def list_dataset_versions(
    workspace_id: str,
    dataset_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    ds = dataset_service.get_dataset(db, ws.id, dataset_id)
    if ds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    versions = dataset_service.list_dataset_versions(db, dataset_id)
    return {"versions": [DatasetVersionResponse.model_validate(v) for v in versions]}


@router.post(
    "/workspaces/{workspace_id}/datasets/{dataset_id}/versions/{version_id}/finalize",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def finalize_dataset_version(
    workspace_id: str,
    dataset_id: str,
    version_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DATASETS_UPDATE)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    try:
        ver = dataset_service.finalize_dataset_version(
            db=db,
            workspace_id=ws.id,
            dataset_id=dataset_id,
            version_id=version_id,
        )
        return {"version": DatasetVersionResponse.model_validate(ver)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
