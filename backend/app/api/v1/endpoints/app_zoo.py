"""REST API endpoints for Milestone 12 App Zoo and Enterprise Application Catalog."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.catalog import (
    AppDefinition,
    AppVersion,
    CatalogVisibility,
    PublicationStatus,
)
from app.models.identity import User
from app.models.organization import MembershipStatus, OrganizationMembership, Workspace
from app.modules.auth.dependencies import get_current_active_user, require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.zoo.app_catalog_service import AppCatalogService
from app.modules.zoo.exceptions import (
    DependencyRevocationError,
    InvalidManifestError,
    ListingNotFoundError,
    ListingReviewError,
    UnapprovedReleaseError,
)
from app.modules.zoo.schemas import (
    AppListingSummary,
    CreateAppDefinitionRequest,
    CreateAppListingRequest,
    CreateAppVersionRequest,
    PaginatedListResponse,
    ReviewListingRequest,
)

router = APIRouter(tags=["App Zoo & Enterprise Application Catalog"])


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
# App Definitions & Versioning
# =========================================================================


@router.post(
    "/workspaces/{workspace_id}/app-zoo/definitions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def create_app_definition_endpoint(
    workspace_id: str,
    payload: CreateAppDefinitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        app_def = AppCatalogService.create_app_definition(
            db=db,
            workspace_id=ws.id,
            organization_id=ws.organization_id,
            user_id=current_user.id,
            name=payload.name,
            description=payload.description,
            app_key=payload.app_key,
            category=payload.category,
        )
        return {
            "id": app_def.id,
            "app_key": app_def.app_key,
            "name": app_def.name,
            "category": app_def.category,
        }
    except InvalidManifestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/app-zoo/definitions",
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_READ))],
)
def list_app_definitions_endpoint(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    ws = _verify_workspace_access(db, workspace_id)
    defs = db.query(AppDefinition).filter(AppDefinition.workspace_id == ws.id).all()
    res = []
    for d in defs:
        res.append({
            "id": d.id,
            "app_key": d.app_key,
            "name": d.name,
            "description": d.description,
            "category": d.category,
            "version_count": len(d.versions),
            "created_at": d.created_at.isoformat(),
        })
    return res


@router.post(
    "/workspaces/{workspace_id}/app-zoo/definitions/{app_definition_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def create_app_version_endpoint(
    workspace_id: str,
    app_definition_id: str,
    payload: CreateAppVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _verify_workspace_access(db, workspace_id)
    try:
        ver = AppCatalogService.create_app_version(
            db=db,
            app_definition_id=app_definition_id,
            user_id=current_user.id,
            version_tag=payload.version_tag,
            description=payload.description,
            capabilities=payload.capabilities,
            supported_input_types=payload.supported_input_types,
            supported_output_types=payload.supported_output_types,
            supported_languages=payload.supported_languages,
            license_id=payload.license_id,
            min_ram_mb=payload.min_ram_mb,
            min_vram_mb=payload.min_vram_mb,
            target_hardware_key=payload.target_hardware_key,
            model_dependencies=payload.model_dependencies,
        )
        return {
            "id": ver.id,
            "version_tag": ver.version_tag,
            "manifest_digest": ver.manifest_digest,
            "dependency_count": len(ver.model_dependencies),
        }
    except (UnapprovedReleaseError, DependencyRevocationError, InvalidManifestError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =========================================================================
# App Listings Management
# =========================================================================


@router.post(
    "/workspaces/{workspace_id}/app-zoo/listings",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def create_app_listing_endpoint(
    workspace_id: str,
    payload: CreateAppListingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    ws = _verify_workspace_access(db, workspace_id)
    try:
        listing = AppCatalogService.create_app_listing(
            db=db,
            workspace_id=ws.id,
            organization_id=ws.organization_id,
            user_id=current_user.id,
            app_version_id=payload.app_version_id,
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
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/workspaces/{workspace_id}/app-zoo/listings",
    response_model=PaginatedListResponse,
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_READ))],
)
def list_workspace_app_listings_endpoint(
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
    items, total = AppCatalogService.search_and_list_apps(
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
        app_def: AppDefinition = it.app_definition
        app_ver: AppVersion = it.app_version
        summaries.append(
            AppListingSummary(
                id=it.id,
                organization_id=it.organization_id,
                workspace_id=it.workspace_id,
                app_definition_id=it.app_definition_id,
                app_version_id=it.app_version_id,
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
                app_name=app_def.name if app_def else None,
                app_key=app_def.app_key if app_def else None,
                version_tag=app_ver.version_tag if app_ver else None,
                dependency_count=len(app_ver.model_dependencies) if app_ver else 0,
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
    "/workspaces/{workspace_id}/app-zoo/listings/{listing_id}",
    dependencies=[Depends(require_ws_permission(WorkspacePermission.CATALOG_READ))],
)
def get_workspace_app_listing_detail_endpoint(
    workspace_id: str,
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _verify_workspace_access(db, workspace_id)
    try:
        detail = AppCatalogService.get_app_listing_detail(db, listing_id)
        listing = detail["listing"]
        ver = detail["app_version"]
        app_def = detail["app_definition"]
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
            "app_definition": {
                "id": app_def.id,
                "name": app_def.name,
                "app_key": app_def.app_key,
                "category": app_def.category,
            },
            "app_version": {
                "id": ver.id,
                "version_tag": ver.version_tag,
                "manifest_digest": ver.manifest_digest,
                "license_id": ver.license_id,
                "capabilities": ver.capabilities,
                "supported_input_types": ver.supported_input_types,
                "supported_output_types": ver.supported_output_types,
                "supported_languages": ver.supported_languages,
                "min_ram_mb": ver.min_ram_mb,
                "min_vram_mb": ver.min_vram_mb,
                "target_hardware_key": ver.target_hardware_key,
            },
            "dependencies": detail["dependencies"],
            "hardware_badges": detail["hardware_badges"],
            "installation_snippets": detail["installation_snippets"],
            "version_history": detail["version_history"],
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/app-zoo/listings/{listing_id}/submit",
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_MANAGE)),
    ],
)
def submit_app_listing_endpoint(
    workspace_id: str,
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    _verify_workspace_access(db, workspace_id)
    try:
        listing = AppCatalogService.submit_app_for_review(db, listing_id, current_user.id)
        return {
            "id": listing.id,
            "publication_status": listing.publication_status.value,
            "message": "App listing submitted for review",
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ListingReviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/workspaces/{workspace_id}/app-zoo/listings/{listing_id}/review",
    dependencies=[
        Depends(require_csrf),
        Depends(require_ws_permission(WorkspacePermission.CATALOG_PUBLISH)),
    ],
)
def review_app_listing_endpoint(
    workspace_id: str,
    listing_id: str,
    payload: ReviewListingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _verify_workspace_access(db, workspace_id)
    try:
        listing = AppCatalogService.review_and_publish_app(
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
    except (ListingReviewError, UnapprovedReleaseError, DependencyRevocationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =========================================================================
# Discovery Endpoints (Cross-Workspace / Organization / Public)
# =========================================================================


@router.get(
    "/zoo/apps",
    response_model=PaginatedListResponse,
)
def discover_apps_endpoint(
    query: str | None = Query(None),
    category: str | None = Query(None),
    visibility: CatalogVisibility | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedListResponse:
    user_org_ids = _get_user_org_ids(db, current_user.id)
    org_id = next(iter(user_org_ids), None)

    items, total = AppCatalogService.search_and_list_apps(
        db=db,
        workspace_id=None,
        organization_id=org_id,
        query_text=query,
        category=category,
        visibility=visibility,
        status=PublicationStatus.PUBLISHED,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    summaries = []
    for it in items:
        app_def: AppDefinition = it.app_definition
        app_ver: AppVersion = it.app_version
        summaries.append(
            AppListingSummary(
                id=it.id,
                organization_id=it.organization_id,
                workspace_id=it.workspace_id,
                app_definition_id=it.app_definition_id,
                app_version_id=it.app_version_id,
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
                app_name=app_def.name if app_def else None,
                app_key=app_def.app_key if app_def else None,
                version_tag=app_ver.version_tag if app_ver else None,
                dependency_count=len(app_ver.model_dependencies) if app_ver else 0,
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
    "/zoo/apps/{listing_id}",
)
def get_app_discovery_detail_endpoint(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    try:
        detail = AppCatalogService.get_app_listing_detail(db, listing_id)
        listing = detail["listing"]
        ver = detail["app_version"]
        app_def = detail["app_definition"]

        if listing.visibility != CatalogVisibility.PUBLIC:
            user_org_ids = _get_user_org_ids(db, current_user.id)
            if listing.organization_id not in user_org_ids:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App listing not found")

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
            "app_definition": {
                "id": app_def.id,
                "name": app_def.name,
                "app_key": app_def.app_key,
                "category": app_def.category,
            },
            "app_version": {
                "id": ver.id,
                "version_tag": ver.version_tag,
                "manifest_digest": ver.manifest_digest,
                "license_id": ver.license_id,
                "capabilities": ver.capabilities,
                "supported_input_types": ver.supported_input_types,
                "supported_output_types": ver.supported_output_types,
                "supported_languages": ver.supported_languages,
                "min_ram_mb": ver.min_ram_mb,
                "min_vram_mb": ver.min_vram_mb,
                "target_hardware_key": ver.target_hardware_key,
            },
            "dependencies": detail["dependencies"],
            "hardware_badges": detail["hardware_badges"],
            "installation_snippets": detail["installation_snippets"],
            "version_history": detail["version_history"],
        }
    except ListingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
