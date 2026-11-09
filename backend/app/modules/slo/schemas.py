"""Pydantic schemas for Service Level Objectives (SLOs) and SLI Snapshots."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SloCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    target_percentage: float = Field(default=99.5, ge=0.0, le=100.0)
    rolling_window_days: int = Field(default=30, ge=1, le=365)
    metric_key: str = Field(default="runtime_request_duration_ms", max_length=100)
    good_events_definition: str = Field(default="latency_ms <= 2000")
    is_enabled: bool = True


class SloUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_percentage: float | None = None
    rolling_window_days: int | None = None
    is_enabled: bool | None = None


class SloRead(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    target_percentage: float
    rolling_window_days: int
    metric_key: str
    good_events_definition: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SliSnapshotRead(BaseModel):
    id: str
    slo_id: str
    customer_site_id: str | None = None
    window_start: datetime
    window_end: datetime
    total_events: int
    good_events: int
    current_sli_percentage: float
    error_budget_remaining_percentage: float
    has_sufficient_data: bool
    burn_rate: float = 1.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
