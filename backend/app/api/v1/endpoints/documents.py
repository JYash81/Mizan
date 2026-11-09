"""Document management and processing API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.documents.schemas import (
    DocumentDetailResponse,
    DocumentResponse,
    ProcessingJobResponse,
)
from app.modules.documents.services import document_service, job_service
from app.modules.documents.services.document_service import DocumentDuplicateError
from app.modules.documents.services.file_validator import FileValidationError
from app.modules.storage import StorageBucket, get_storage_provider

router = APIRouter(tags=["Documents"])


@router.post(
    "/workspaces/{workspace_id}/datasets/{dataset_id}/versions/{version_id}/documents/upload",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_document(
    workspace_id: str,
    dataset_id: str,
    version_id: str,
    file: UploadFile = File(...),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_UPLOAD)
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    storage = get_storage_provider()

    try:
        content = await file.read()
        doc, job = document_service.upload_document(
            db=db,
            storage=storage,
            workspace_id=ws.id,
            dataset_version_id=version_id,
            filename=file.filename or "unnamed_document.bin",
            content=content,
            actor_id=current_user.id,
        )
        return {
            "document": DocumentResponse.model_validate(doc),
            "job": ProcessingJobResponse.model_validate(job),
        }
    except DocumentDuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/workspaces/{workspace_id}/datasets/{dataset_id}/versions/{version_id}/documents",
    status_code=status.HTTP_200_OK,
)
def list_documents(
    workspace_id: str,
    dataset_id: str,
    version_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    documents = document_service.list_documents(db, version_id)
    return {"documents": [DocumentResponse.model_validate(d) for d in documents]}


@router.get(
    "/workspaces/{workspace_id}/documents/{document_id}",
    status_code=status.HTTP_200_OK,
)
def get_document(
    workspace_id: str,
    document_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    doc = document_service.get_document(db, ws.id, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    storage = get_storage_provider()
    extracted_text = doc.extracted_text_sample

    # If full extracted text was saved to storage, retrieve it
    if doc.extracted_text_key and storage.object_exists(
        StorageBucket.RAW_UPLOADS, doc.extracted_text_key
    ):
        try:
            full_text_bytes, _ = storage.get_object(
                StorageBucket.RAW_UPLOADS, doc.extracted_text_key
            )
            extracted_text = full_text_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

    detail = DocumentDetailResponse.model_validate(doc)
    detail.extracted_text = extracted_text
    return {"document": detail}


@router.delete(
    "/workspaces/{workspace_id}/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def delete_document(
    workspace_id: str,
    document_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_DELETE)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    storage = get_storage_provider()
    deleted = document_service.delete_document(db, storage, ws.id, document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return {"status": "deleted", "id": document_id}


@router.post(
    "/workspaces/{workspace_id}/documents/{document_id}/reprocess",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_csrf)],
)
def reprocess_document(
    workspace_id: str,
    document_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_UPLOAD)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    storage = get_storage_provider()
    try:
        job = document_service.reprocess_document(db, storage, ws.id, document_id)
        doc = document_service.get_document(db, ws.id, document_id)
        return {
            "document": DocumentResponse.model_validate(doc) if doc else None,
            "job": ProcessingJobResponse.model_validate(job),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/workspaces/{workspace_id}/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
)
def get_job_status(
    workspace_id: str,
    job_id: str,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.DOCUMENTS_READ)
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ws, _, _ = context
    job = job_service.get_job(db, ws.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return {"job": ProcessingJobResponse.model_validate(job)}
