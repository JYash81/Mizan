"""Pydantic schemas for Operational Incident Management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.observability import IncidentSeverity, IncidentStatus


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    severity: IncidentSeverity = IncidentSeverity.SEV2
    customer_site_id: str | None = None
    runtime_application_id: str | None = None
    primary_alert_id: str | None = None
    assigned_to: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    assigned_to: str | None = None
    status_change_note: str | None = None


class IncidentEventRead(BaseModel):
    id: str
    incident_id: str
    event_type: str
    description: str
    actor_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentRead(BaseModel):
    id: str
    workspace_id: str
    incident_number: int
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    customer_site_id: str | None = None
    runtime_application_id: str | None = None
    primary_alert_id: str | None = None
    assigned_to: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    events: list[IncidentEventRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
