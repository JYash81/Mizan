"""Infrastructure Pricing Catalog and Cost Estimation API Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.organization import OrganizationMembership, Workspace, WorkspaceRole
from app.modules.auth.dependencies import require_csrf
from app.modules.authorization.dependencies import require_ws_permission
from app.modules.authorization.permissions import WorkspacePermission
from app.modules.cost.cost_estimator import CostEstimatorService
from app.modules.cost.pricing_catalog import PricingCatalogService
from app.modules.cost.schemas.cost import (
    CostEstimateRequest,
    CostEstimateResponse,
    CostScenarioComparisonResponse,
    PricingCatalogCreate,
    PricingCatalogEntryResponse,
)

router = APIRouter(tags=["Cost Estimation & Pricing"])
catalog_svc = PricingCatalogService()
cost_estimator = CostEstimatorService(catalog_service=catalog_svc)


@router.get(
    "/workspaces/{workspace_id}/cost/pricing",
    response_model=list[PricingCatalogEntryResponse],
)
def list_pricing_catalog(
    workspace_id: str,
    provider_name: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    catalog_version: str | None = Query(default=None),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_READ)
    ),
    db: Session = Depends(get_db),
) -> list[PricingCatalogEntryResponse]:
    """List infrastructure pricing rates with versioning and provenance tracking."""
    entries = catalog_svc.list_entries(
        db,
        provider_name=provider_name,
        resource_type=resource_type,
        catalog_version=catalog_version,
    )
    return [PricingCatalogEntryResponse.model_validate(e) for e in entries]


@router.post(
    "/workspaces/{workspace_id}/cost/pricing",
    response_model=PricingCatalogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_or_update_pricing(
    workspace_id: str,
    payload: PricingCatalogCreate,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.HARDWARE_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PricingCatalogEntryResponse:
    """Create or update a pricing entry with explicit provenance."""
    entry = catalog_svc.create_or_update_entry(db, data=payload)
    return PricingCatalogEntryResponse.model_validate(entry)


@router.post(
    "/workspaces/{workspace_id}/cost/estimate",
    response_model=CostEstimateResponse,
)
def estimate_infrastructure_cost(
    workspace_id: str,
    payload: CostEstimateRequest,
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_ESTIMATE)
    ),
    db: Session = Depends(get_db),
) -> CostEstimateResponse:
    """Calculate deterministic, decimal-precision cost estimate with billing-unit rounding."""
    return cost_estimator.calculate_cost(db, req=payload)


@router.post(
    "/workspaces/{workspace_id}/cost/scenarios",
    response_model=CostScenarioComparisonResponse,
)
def compare_cost_scenarios(
    workspace_id: str,
    scenarios: list[CostEstimateRequest],
    workload_description: str = Query(default="Multi-scenario infrastructure comparison"),
    context: tuple[Workspace, OrganizationMembership, WorkspaceRole | None] = Depends(
        require_ws_permission(WorkspacePermission.COST_READ)
    ),
    db: Session = Depends(get_db),
) -> CostScenarioComparisonResponse:
    """Compare multiple pricing and provider scenarios side-by-side."""
    if not scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one scenario must be provided.",
        )
    return cost_estimator.compare_scenarios(
        db, scenarios=scenarios, workload_description=workload_description
    )
