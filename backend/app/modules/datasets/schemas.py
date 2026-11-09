"""Pydantic schemas for Datasets and Dataset Versions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class DatasetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class DatasetVersionCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_id: str
    version_number: int
    name: str
    description: str | None
    status: str
    total_documents: int
    total_raw_bytes: int
    content_hash: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    description: str | None
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    active_version: DatasetVersionResponse | None = None

    model_config = ConfigDict(from_attributes=True)
