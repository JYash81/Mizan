"""REST API endpoints for Milestone 12 Model Zoo and Enterprise Model Catalog."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import (
    CatalogVisibility,
    HardwareCompatibilityBadge,
    PublicationStatus,
)
from app.models.identity import User
from app.models.organization import MembershipStatus, OrganizationMembership, Workspace
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.zoo.artifact_download_service import ArtifactDownloadService
from app.modules.zoo.exceptions import (
    CatalogError,
    DownloadNotPermittedError,
    ListingNotFoundError,
    ListingNotPublishedError,
    ListingReviewError,
    PublicPublicationNotAllowedError,
    RevokedReleaseError,
    UnapprovedReleaseError,
)
from app.modules.zoo.model_catalog_service import ModelCatalogService
from app.modules.zoo.schemas import (
    CreateModelListingRequest,
    ModelListingSummary,
    PaginatedListResponse,
    ReviewListingRequest,
    SuspendListingRequest,
)

router = APIRouter(tags=["Model Zoo & Enterprise Model Catalog"])


def _verify_workspace_access(db: Session, workspace_id: str) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws


def _get_user_org_ids(db: Session, user_id: str) -> set[str]:
    stmt = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.membership_status == MembershipStatus.ACTIVE,
    )
    return set(db.scalars(stmt).all())


# =========================================================================
# Workspace-Scoped Model Listing Management
# =========================================================================


@router.get(
    "/workspaces/{workspace_id}/model-zoo/listings",
    response_model=PaginatedListResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_READ))],
)
def list_workspace_model_listings_endpoint(
    workspace_id: str,
    query: str | None = Query(None),
    category: str | None = Query(None),
    publication_status: PublicationStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedListResponse:
    ws = _verify_workspace_access(db, workspace_id)
    items, total = ModelCatalogService.search_and_list_models(
        db=db,
        workspace_id=ws.id,
        organization_id=ws.organization_id,
        query_text=query,
        category=category,
        status=publication_status,
        page=page,
        page_size=page_size,
    )
    summaries = []
    for it in items:
        summaries.append(
            ModelListingSummary(
                id=it.id,
                organization_id=it.organization_id,
                workspace_id=it.workspace_id,
                model_family_id=it.model_family_id,
                model_version_id=it.model_version_id,
                title=it.title,
                slug=it.slug,
                description=it.description,
                category=it.category,
                tags=it.tags,
                visibility=it.visibility.value,
                publication_status=it.publication_status.value,
                distribution_status=it.distribution_status.value,
                publication_digest=it.publication_digest,
                is_featured=it.is_featured,
                created_at=it.created_at.isoformat(),
                published_at=it.published_at.isoformat() if it.published_at else None,
                model_family_name=it.model_family.name if it.model_family else None,
                model_family_slug=it.model_family.slug if it.model_family else None,
                version_tag=it.model_version.version_tag if it.model_version else None,
                source_model_key=it.model_version.source_model_key if it.model_version else None,
                final_evaluation_score=it.model_version.final_evaluation_score if it.model_version else None,
            )
        )
    return PaginatedListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post(
    "/workspaces/{workspace_id}/model-zoo/listings",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def create_model_listing_endpoint(
    workspace_id: str,
    payload: CreateModelListingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        listing = ModelCatalogService.create_model_listing(
            db=db,
            workspace_id=ws.id,
            organization_id=ws.organization_id,
            user_id=current_user.id,
            model_version_id=payload.model_version_id,
            title=payload.title,
            description=payload.description,
            slug=payload.slug,
            detailed_description=payload.detailed_description,
            category=payload.category,
            tags=payload.tags,
            visibility=payload.visibility,
            distribution_status=payload.distribution_status,
        )
        return {
            "id": listing.id,
            "title": listing.title,
            "slug": listing.slug,
            "publication_status": listing.publication_status.value,
            "visibility": listing.visibility.value,
        }
    except (UnapprovedReleaseError, RevokedReleaseError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CatalogError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/model-zoo/listings/{listing_id}",
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_READ))],
)
def get_workspace_model_listing_detail_endpoint(
    workspace_id: str,
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _verify_workspace_access(db, workspace_id)
    try:
        detail = ModelCatalogService.get_model_listing_detail(db, listing_id)
        listing = detail["listing"]
        mv = detail["model_version"]
        mf = detail["model_family"]
        return {
            "listing": {
                "id": listing.id,
                "title": listing.title,
                "slug": listing.slug,
                "description": listing.description,
                "detailed_description": listing.detailed_description,
                "category": listing.category,
                "tags": listing.tags,
                "visibility": listing.visibility.value,
                "publication_status": listing.publication_status.value,
                "distribution_status": listing.distribution_status.value,
                "publication_digest": listing.publication_digest,
                "created_at": listing.created_at.isoformat(),
                "published_at": listing.published_at.isoformat() if listing.published_at else None,
            },
            "model_family": {
                "id": mf.id,
                "name": mf.name,
                "slug": mf.slug,
                "task_type": mf.task_type,
            },
            "model_version": {
                "id": mv.id,
                "version_tag": mv.version_tag,
                "source_model_key": mv.source_model_key,
                "source_model_revision": mv.source_model_revision,
                "recipe_key": mv.recipe_key,
                "base_evaluation_score": mv.base_evaluation_score,
                "final_evaluation_score": mv.final_evaluation_score,
                "quality_delta": mv.quality_delta,
                "min_ram_mb": mv.min_ram_mb,
                "min_vram_mb": mv.min_vram_mb,
                "target_hardware_key": mv.target_hardware_key,
                "release_manifest_digest": mv.release_manifest_digest,
            },
            "artifacts": [
                {
                    "id": a.id,
                    "artifact_type": a.artifact_type.value,
                    "format": a.format,
                    "quantization_type": a.quantization_type,
                    "file_size_bytes": a.file_size_bytes,
                    "sha256": a.sha256,
                    "is_primary_weights": a.is_primary_weights,
                }
                for a in mv.artifacts or []
            ],
            "hardware_badges": detail["hardware_badges"],
            "installation_snippets": detail["installation_snippets"],
            "version_history": detail["version_history"],
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/model-zoo/listings/{listing_id}/submit",
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def submit_model_listing_endpoint(
    workspace_id: str,
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    _verify_workspace_access(db, workspace_id)
    try:
        listing = ModelCatalogService.submit_for_review(db, listing_id, current_user.id)
        return {
            "id": listing.id,
            "publication_status": listing.publication_status.value,
            "message": "Listing submitted for catalog review",
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ListingReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/model-zoo/listings/{listing_id}/review",
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_PUBLISH)),
    ],
)
def review_model_listing_endpoint(
    workspace_id: str,
    listing_id: str,
    payload: ReviewListingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _verify_workspace_access(db, workspace_id)
    try:
        listing = ModelCatalogService.review_and_publish(
            db=db,
            listing_id=listing_id,
            reviewer_id=current_user.id,
            decision=payload.decision,
            rationale=payload.rationale,
        )
        return {
            "id": listing.id,
            "publication_status": listing.publication_status.value,
            "publication_digest": listing.publication_digest,
            "published_at": listing.published_at.isoformat() if listing.published_at else None,
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ListingReviewError, UnapprovedReleaseError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PublicPublicationNotAllowedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/model-zoo/listings/{listing_id}/suspend",
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_PUBLISH)),
    ],
)
def suspend_model_listing_endpoint(
    workspace_id: str,
    listing_id: str,
    payload: SuspendListingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    _verify_workspace_access(db, workspace_id)
    try:
        listing = ModelCatalogService.suspend_listing(db, listing_id, current_user.id, payload.reason)
        return {
            "id": listing.id,
            "publication_status": listing.publication_status.value,
            "message": "Listing suspended",
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/model-zoo/listings/{listing_id}/artifacts/{artifact_id}/download",
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_DOWNLOAD))],
)
def download_model_artifact_endpoint(
    workspace_id: str,
    listing_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        res = ArtifactDownloadService.authorize_artifact_download(
            db=db,
            listing_id=listing_id,
            artifact_id=artifact_id,
            user_id=current_user.id,
            user_workspace_id=ws.id,
            user_organization_id=ws.organization_id,
        )
        return res
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ListingNotPublishedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (UnapprovedReleaseError, RevokedReleaseError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DownloadNotPermittedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# =========================================================================
# Discovery Catalog Endpoints (Cross-Workspace / Organization / Public)
# =========================================================================


@router.get(
    "/zoo/models",
    response_model=PaginatedListResponse,
)
def discover_models_endpoint(
    query: str | None = Query(None),
    category: str | None = Query(None),
    visibility: CatalogVisibility | None = Query(None),
    hardware_badge: HardwareCompatibilityBadge | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedListResponse:
    """Discover approved and published models in the enterprise Model Zoo."""
    # Find user's primary organization from active memberships
    user_org_ids = _get_user_org_ids(db, current_user.id)
    org_id = next(iter(user_org_ids), None)

    items, total = ModelCatalogService.search_and_list_models(
        db=db,
        workspace_id=None,
        organization_id=org_id,
        query_text=query,
        category=category,
        visibility=visibility,
        status=PublicationStatus.PUBLISHED,
        hardware_badge=hardware_badge,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    summaries = []
    for it in items:
        summaries.append(
            ModelListingSummary(
                id=it.id,
                organization_id=it.organization_id,
                workspace_id=it.workspace_id,
                model_family_id=it.model_family_id,
                model_version_id=it.model_version_id,
                title=it.title,
                slug=it.slug,
                description=it.description,
                category=it.category,
                tags=it.tags,
                visibility=it.visibility.value,
                publication_status=it.publication_status.value,
                distribution_status=it.distribution_status.value,
                publication_digest=it.publication_digest,
                is_featured=it.is_featured,
                created_at=it.created_at.isoformat(),
                published_at=it.published_at.isoformat() if it.published_at else None,
                model_family_name=it.model_family.name if it.model_family else None,
                model_family_slug=it.model_family.slug if it.model_family else None,
                version_tag=it.model_version.version_tag if it.model_version else None,
                source_model_key=it.model_version.source_model_key if it.model_version else None,
                final_evaluation_score=it.model_version.final_evaluation_score if it.model_version else None,
            )
        )
    return PaginatedListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get(
    "/zoo/models/{listing_id}",
)
def get_model_discovery_detail_endpoint(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Retrieve full catalog details and installation guides for a published model."""
    try:
        detail = ModelCatalogService.get_model_listing_detail(db, listing_id)
        listing = detail["listing"]
        mv = detail["model_version"]
        mf = detail["model_family"]

        # If not public, verify organization/workspace access
        if listing.visibility != CatalogVisibility.PUBLIC:
            user_org_ids = _get_user_org_ids(db, current_user.id)
            if listing.organization_id not in user_org_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model listing not found")

        return {
            "listing": {
                "id": listing.id,
                "title": listing.title,
                "slug": listing.slug,
                "description": listing.description,
                "detailed_description": listing.detailed_description,
                "category": listing.category,
                "tags": listing.tags,
                "visibility": listing.visibility.value,
                "publication_status": listing.publication_status.value,
                "distribution_status": listing.distribution_status.value,
                "publication_digest": listing.publication_digest,
                "created_at": listing.created_at.isoformat(),
                "published_at": listing.published_at.isoformat() if listing.published_at else None,
            },
            "model_family": {
                "id": mf.id,
                "name": mf.name,
                "slug": mf.slug,
                "task_type": mf.task_type,
            },
            "model_version": {
                "id": mv.id,
                "version_tag": mv.version_tag,
                "source_model_key": mv.source_model_key,
                "source_model_revision": mv.source_model_revision,
                "recipe_key": mv.recipe_key,
                "base_evaluation_score": mv.base_evaluation_score,
                "final_evaluation_score": mv.final_evaluation_score,
                "quality_delta": mv.quality_delta,
                "min_ram_mb": mv.min_ram_mb,
                "min_vram_mb": mv.min_vram_mb,
                "target_hardware_key": mv.target_hardware_key,
                "release_manifest_digest": mv.release_manifest_digest,
            },
            "artifacts": [
                {
                    "id": a.id,
                    "artifact_type": a.artifact_type.value,
                    "format": a.format,
                    "quantization_type": a.quantization_type,
                    "file_size_bytes": a.file_size_bytes,
                    "sha256": a.sha256,
                    "is_primary_weights": a.is_primary_weights,
                }
                for a in mv.artifacts or []
            ],
            "hardware_badges": detail["hardware_badges"],
            "installation_snippets": detail["installation_snippets"],
            "version_history": detail["version_history"],
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
