"""Pydantic schemas for Automated Rollback Policies and Execution Audits."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.observability import RollbackMode


class RollbackPolicyCreate(BaseModel):
    runtime_application_id: str | None = None
    mode: RollbackMode = RollbackMode.MANUAL_ONLY
    evaluation_window_seconds: int = Field(default=300, ge=30, le=3600)
    error_rate_threshold_percentage: float = Field(default=5.0, ge=0.1, le=100.0)
    latency_p95_threshold_ms: float = Field(default=2000.0, ge=10.0, le=60000.0)
    cooldown_seconds: int = Field(default=600, ge=60, le=86400)
    max_automatic_attempts_per_release: int = Field(default=1, ge=1, le=10)
    require_golden_test_pass: bool = True
    require_gate3_active: bool = True


class RollbackPolicyUpdate(BaseModel):
    mode: RollbackMode | None = None
    evaluation_window_seconds: int | None = None
    error_rate_threshold_percentage: float | None = None
    latency_p95_threshold_ms: float | None = None
    cooldown_seconds: int | None = None
    max_automatic_attempts_per_release: int | None = None
    require_golden_test_pass: bool | None = None
    require_gate3_active: bool | None = None


class RollbackPolicyRead(BaseModel):
    id: str
    workspace_id: str
    runtime_application_id: str | None = None
    mode: RollbackMode
    evaluation_window_seconds: int
    error_rate_threshold_percentage: float
    latency_p95_threshold_ms: float
    cooldown_seconds: int
    max_automatic_attempts_per_release: int
    require_golden_test_pass: bool
    require_gate3_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollbackEligibilityCheckResult(BaseModel):
    is_eligible: bool
    reasons: list[str] = Field(default_factory=list)
    current_slot_name: str
    target_slot_name: str
    target_model_version_id: str | None = None
    target_is_gate3_approved: bool = False
    target_is_revoked: bool = False
    flapping_detected: bool = False


class RollbackTriggerRequest(BaseModel):
    runtime_application_id: str
    reason: str = Field(..., max_length=500)


class RollbackExecutionEventRead(BaseModel):
    id: str
    runtime_application_id: str
    from_slot_name: str
    to_slot_name: str
    from_model_version_id: str | None = None
    to_model_version_id: str | None = None
    trigger_type: str
    trigger_reason: str
    verification_passed: bool
    golden_test_run_id: str | None = None
    status: str
    error_detail: str | None = None
    executed_by: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
