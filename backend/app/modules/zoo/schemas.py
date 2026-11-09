"""Pydantic V2 schemas for Milestone 12: Model Zoo, App Zoo, and Enterprise Catalog."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.catalog import CatalogVisibility, DistributionStatus


class CreateModelListingRequest(BaseModel):
    model_version_id: str
    title: str = Field(..., min_length=2, max_length=255)
    slug: str | None = None
    description: str = Field(..., min_length=5)
    detailed_description: str | None = None
    category: str = "GENERAL_CHAT"
    tags: list[str] = []
    visibility: CatalogVisibility = CatalogVisibility.WORKSPACE
    distribution_status: DistributionStatus = DistributionStatus.DOWNLOADABLE


class UpdateModelListingRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    detailed_description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    visibility: CatalogVisibility | None = None
    distribution_status: DistributionStatus | None = None


class ReviewListingRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    rationale: str = Field(..., min_length=5)


class SuspendListingRequest(BaseModel):
    reason: str = Field(..., min_length=5)


class CreateAppDefinitionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    app_key: str | None = None
    description: str = Field(..., min_length=5)
    category: str = "DOCUMENT_ASSISTANT"


class CreateAppVersionRequest(BaseModel):
    version_tag: str = Field(..., min_length=1, max_length=64)
    description: str | None = None
    capabilities: list[str] = ["TEXT_GENERATION"]
    supported_input_types: list[str] = ["text/plain"]
    supported_output_types: list[str] = ["text/markdown"]
    supported_languages: list[str] = ["en"]
    license_id: str = "Apache-2.0"
    min_ram_mb: float = 4096.0
    min_vram_mb: float = 0.0
    target_hardware_key: str | None = None
    model_dependencies: list[dict[str, str]] = []


class CreateAppListingRequest(BaseModel):
    app_version_id: str
    title: str = Field(..., min_length=2, max_length=255)
    slug: str | None = None
    description: str = Field(..., min_length=5)
    detailed_description: str | None = None
    category: str = "DOCUMENT_ASSISTANT"
    tags: list[str] = []
    visibility: CatalogVisibility = CatalogVisibility.WORKSPACE
    distribution_status: DistributionStatus = DistributionStatus.METADATA_ONLY


class ModelListingSummary(BaseModel):
    id: str
    organization_id: str
    workspace_id: str
    model_family_id: str
    model_version_id: str
    title: str
    slug: str
    description: str
    category: str
    tags: list[str]
    visibility: str
    publication_status: str
    distribution_status: str
    publication_digest: str | None
    is_featured: bool
    created_at: str
    published_at: str | None

    model_family_name: str | None = None
    model_family_slug: str | None = None
    version_tag: str | None = None
    source_model_key: str | None = None
    final_evaluation_score: float | None = None


class AppListingSummary(BaseModel):
    id: str
    organization_id: str
    workspace_id: str
    app_definition_id: str
    app_version_id: str
    title: str
    slug: str
    description: str
    category: str
    tags: list[str]
    visibility: str
    publication_status: str
    distribution_status: str
    publication_digest: str | None
    is_featured: bool
    created_at: str
    published_at: str | None

    app_name: str | None = None
    app_key: str | None = None
    version_tag: str | None = None
    dependency_count: int = 0


class PaginatedListResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
