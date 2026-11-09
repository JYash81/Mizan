"""Pydantic schemas for Alerting, Rules, Instances, Silences, and Notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.observability import AlertSeverity, AlertStatus


class AlertRuleCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    metric_key: str = Field(..., max_length=100)
    condition_operator: str = Field(default="GT", max_length=8)
    threshold: float
    duration_seconds: int = Field(default=60, ge=10, le=86400)
    consecutive_breaches: int = Field(default=1, ge=1, le=100)
    severity: AlertSeverity = AlertSeverity.WARNING
    is_enabled: bool = True
    cooldown_seconds: int = Field(default=300, ge=0, le=86400)
    target_slot: str = Field(default="ANY", max_length=16)


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    threshold: float | None = None
    duration_seconds: int | None = None
    consecutive_breaches: int | None = None
    severity: AlertSeverity | None = None
    is_enabled: bool | None = None
    cooldown_seconds: int | None = None


class AlertRuleRead(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    metric_key: str
    condition_operator: str
    threshold: float
    duration_seconds: int
    consecutive_breaches: int
    severity: AlertSeverity
    is_enabled: bool
    cooldown_seconds: int
    target_slot: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertInstanceRead(BaseModel):
    id: str
    rule_id: str
    customer_site_id: str | None = None
    fingerprint: str
    status: AlertStatus
    current_value: float
    breach_count: int
    first_breached_at: datetime | None = None
    last_breached_at: datetime | None = None
    fired_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertAcknowledgeRequest(BaseModel):
    comment: str | None = None


class AlertSilenceCreate(BaseModel):
    rule_id: str | None = None
    customer_site_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(..., max_length=500)


class AlertSilenceRead(BaseModel):
    id: str
    workspace_id: str
    rule_id: str | None = None
    customer_site_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    reason: str
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPolicyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    channel_type: str = Field(default="LOCAL_STORE", max_length=32)
    config: dict[str, Any] = Field(default_factory=dict)
    min_severity: AlertSeverity = AlertSeverity.WARNING
    is_enabled: bool = True


class NotificationPolicyRead(BaseModel):
    id: str
    workspace_id: str
    name: str
    channel_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    min_severity: AlertSeverity
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
