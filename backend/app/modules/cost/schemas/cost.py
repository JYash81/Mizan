"""Pydantic schemas for Infrastructure Pricing Catalog and Cost Estimator."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.hardware import PricingProvenance


class PricingCatalogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_name: str
    resource_type: str
    instance_type: str
    region: str
    currency: str
    hourly_rate: str
    storage_monthly_rate_per_gb: str | None = None
    billing_unit_seconds: int
    source_url: str | None = None
    provenance: PricingProvenance
    effective_from: datetime
    effective_to: datetime | None = None
    is_verified: bool
    catalog_version: str
    created_at: datetime
    updated_at: datetime


class PricingCatalogCreate(BaseModel):
    provider_name: str = Field(min_length=2, max_length=64)
    resource_type: str = Field(min_length=2, max_length=32)
    instance_type: str = Field(min_length=2, max_length=64)
    region: str = Field(min_length=2, max_length=64)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    hourly_rate: str = Field(
        description="Decimal string representation of hourly rate, e.g. '0.5260'"
    )
    storage_monthly_rate_per_gb: str | None = None
    billing_unit_seconds: int = Field(default=3600, ge=1)
    source_url: str | None = None
    provenance: PricingProvenance = Field(default=PricingProvenance.USER_SUPPLIED)
    is_verified: bool = False
    catalog_version: str = Field(default="2026.1")


class CostEstimateRequest(BaseModel):
    provider_name: str = Field(default="reference_cloud")
    instance_type: str = Field(default="NVIDIA_T4_16GB")
    region: str = Field(default="us-east-1")
    duration_hours: float = Field(
        ge=0.01, le=1000.0, description="Estimated or measured workload duration in hours"
    )
    duration_source: str = Field(
        default="USER_SUPPLIED",
        description="M7_MEASURED, USER_SUPPLIED, REFERENCE_ESTIMATE, SIMULATED",
    )
    storage_gb: float = Field(default=0.0, ge=0.0, description="Storage requirement in Gigabytes")
    storage_duration_hours: float | None = Field(default=None, ge=0.0)
    currency: str = Field(default="USD")


class CostBreakdownItem(BaseModel):
    component_name: str
    quantity: float
    unit: str
    rate: str
    subtotal: str
    notes: str | None = None


class CostEstimateResponse(BaseModel):
    total_estimated_cost: str
    currency: str
    status: str  # "AVAILABLE", "UNKNOWN", "PRICE_UNAVAILABLE", "ZERO_SPEND_LOCAL"
    provider_name: str
    instance_type: str
    region: str
    duration_hours: float
    duration_source: str
    billable_hours: float
    billing_unit_seconds: int
    pricing_catalog_version: str
    pricing_provenance: PricingProvenance | None = None
    price_is_verified: bool = False
    cost_breakdown: list[CostBreakdownItem] = Field(default_factory=list)
    min_estimated_cost: str | None = None
    max_estimated_cost: str | None = None
    warnings: list[str] = Field(default_factory=list)
    estimated_at: datetime


class CostScenarioItem(BaseModel):
    scenario_name: str
    hardware_profile_key: str
    provider_name: str
    instance_type: str
    estimated_duration_hours: float
    estimated_total_cost: str
    currency: str
    pricing_provenance: str
    feasibility_notes: str


class CostScenarioComparisonResponse(BaseModel):
    workload_description: str
    scenarios: list[CostScenarioItem] = Field(default_factory=list)
