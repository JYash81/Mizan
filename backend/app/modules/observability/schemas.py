"""Pydantic schemas for Observability, Metrics, Events, and Telemetry Configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelemetryConfigurationRead(BaseModel):
    id: str
    customer_site_id: str
    sync_consent: bool
    consent_granted_by: str | None = None
    consent_granted_at: datetime | None = None
    consent_expires_at: datetime | None = None
    retention_days: int
    metrics_enabled: bool
    events_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryConsentUpdateRequest(BaseModel):
    sync_consent: bool
    retention_days: int = Field(default=30, ge=1, le=365)


class MetricValuePoint(BaseModel):
    metric_key: str
    labels: dict[str, str] = Field(default_factory=dict)
    value: float
    timestamp: datetime


class MetricSeriesRead(BaseModel):
    metric_key: str
    name: str
    metric_type: str
    unit: str
    points: list[MetricValuePoint] = Field(default_factory=list)


class MetricsSummaryResponse(BaseModel):
    site_id: str | None = None
    active_slot: str = "SLOT_A"
    readiness_state: str = "READY"
    requests_total: int = 0
    error_rate_percentage: float = 0.0
    latency_p95_ms: float = 0.0
    latency_avg_ms: float = 0.0
    tokens_per_second: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_allocated_mb: float = 0.0
    vram_allocated_mb: float = 0.0
    firing_alerts_count: int = 0
    slo_status: str = "HEALTHY"
    timestamp: datetime


class OperationalEventCreate(BaseModel):
    customer_site_id: str | None = None
    workspace_id: str | None = None
    event_type: str = Field(..., max_length=64)
    severity: str = Field(default="INFO", max_length=16)
    source_component: str = Field(default="runtime", max_length=64)
    summary: str = Field(..., max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class OperationalEventRead(BaseModel):
    id: str
    customer_site_id: str | None = None
    workspace_id: str | None = None
    event_type: str
    severity: str
    source_component: str
    summary: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
