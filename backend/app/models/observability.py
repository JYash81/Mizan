"""SQLAlchemy models for Milestone 14: Production Telemetry, Monitoring, SLOs, Alerting, Incident Management & Automated Rollback."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MetricType(str, enum.Enum):
    """Supported metric types following Prometheus/OpenTelemetry semantics."""

    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"


class AlertSeverity(str, enum.Enum):
    """Standardized severity levels for operational alerts."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    """Lifecycle states of an individual alert instance."""

    NORMAL = "NORMAL"
    PENDING = "PENDING"
    FIRING = "FIRING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SILENCED = "SILENCED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class RollbackMode(str, enum.Enum):
    """Automated rollback operational modes."""

    DISABLED = "DISABLED"
    MANUAL_ONLY = "MANUAL_ONLY"
    AUTOMATIC = "AUTOMATIC"


class IncidentSeverity(str, enum.Enum):
    """Severity ratings for operational incidents."""

    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentStatus(str, enum.Enum):
    """Lifecycle progression of an operational incident."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# =========================================================================
# 1. Telemetry Configuration & Consent
# =========================================================================


class TelemetryConfiguration(Base):
    """Customer site telemetry synchronization, consent, and retention configuration."""

    __tablename__ = "telemetry_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    sync_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_granted_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    consent_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    metrics_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    events_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )


# =========================================================================
# 2. Metric Definition & Bounded Aggregation
# =========================================================================


class MetricDefinition(Base):
    """Registered metadata schema for system and runtime metrics."""

    __tablename__ = "metric_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    metric_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metric_type: Mapped[MetricType] = mapped_column(
        Enum(MetricType, native_enum=False), default=MetricType.GAUGE, nullable=False
    )
    unit: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    allowed_labels_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    @property
    def allowed_labels(self) -> list[str]:
        try:
            return json.loads(self.allowed_labels_json)
        except Exception:
            return []


class MetricAggregate(Base):
    """Bounded, rolled-up operational metric values preventing unbounded growth."""

    __tablename__ = "metric_aggregates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_type: Mapped[str] = mapped_column(String(16), default="HOURLY", nullable=False)
    labels_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sum_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    p95_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    @property
    def labels(self) -> dict[str, str]:
        try:
            return json.loads(self.labels_json)
        except Exception:
            return {}


# =========================================================================
# 3. Privacy-Safe Operational Events
# =========================================================================


class OperationalEvent(Base):
    """Sanitized, append-only operational audit and lifecycle event journal."""

    __tablename__ = "operational_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False, index=True)
    source_component: Mapped[str] = mapped_column(String(64), default="runtime", nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False, index=True
    )

    @property
    def payload(self) -> dict[str, Any]:
        try:
            return json.loads(self.payload_json)
        except Exception:
            return {}


# =========================================================================
# 4. Alert Rules, Instances, Silences & Notifications
# =========================================================================


class AlertRule(Base):
    """Evaluated alert threshold specification."""

    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    condition_operator: Mapped[str] = mapped_column(String(8), default="GT", nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    consecutive_breaches: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False), default=AlertSeverity.WARNING, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    target_slot: Mapped[str] = mapped_column(String(16), default="ANY", nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    instances: Mapped[list[AlertInstance]] = relationship(
        "AlertInstance", back_populates="rule", cascade="all, delete-orphan"
    )


class AlertInstance(Base):
    """An active or historical alert state tracker with fingerprint deduplication."""

    __tablename__ = "alert_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False), default=AlertStatus.NORMAL, nullable=False, index=True
    )
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    breach_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    labels_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    annotations_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    rule: Mapped[AlertRule] = relationship("AlertRule", back_populates="instances")
    events: Mapped[list[AlertEvent]] = relationship(
        "AlertEvent", back_populates="instance", cascade="all, delete-orphan"
    )

    @property
    def labels(self) -> dict[str, str]:
        try:
            return json.loads(self.labels_json)
        except Exception:
            return {}

    @property
    def annotations(self) -> dict[str, Any]:
        try:
            return json.loads(self.annotations_json)
        except Exception:
            return {}


class AlertEvent(Base):
    """Append-only lifecycle state transitions of an alert instance."""

    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    alert_instance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alert_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    transition_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    instance: Mapped[AlertInstance] = relationship("AlertInstance", back_populates="events")


class AlertSilence(Base):
    """Time-bounded suppression of matching alerts with operator rationale."""

    __tablename__ = "alert_silences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


class NotificationPolicy(Base):
    """Routing rules for operational alerts."""

    __tablename__ = "notification_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(32), default="LOCAL_STORE", nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    min_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False), default=AlertSeverity.WARNING, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    @property
    def config(self) -> dict[str, Any]:
        try:
            return json.loads(self.config_json)
        except Exception:
            return {}


class NotificationDelivery(Base):
    """Audit log of delivered or attempted notifications."""

    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notification_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_instance_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("alert_instances.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="DELIVERED", nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 5. Service Level Objectives (SLOs) & Error Budgets
# =========================================================================


class ServiceLevelObjective(Base):
    """Target percentage and measurement configuration for an SLI."""

    __tablename__ = "service_level_objectives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_percentage: Mapped[float] = mapped_column(Float, default=99.5, nullable=False)
    rolling_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(100), default="runtime_request_duration_ms", nullable=False)
    good_events_definition: Mapped[str] = mapped_column(Text, default="latency_ms <= 2000", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    snapshots: Mapped[list[SliSnapshot]] = relationship(
        "SliSnapshot", back_populates="slo", cascade="all, delete-orphan"
    )


class SliSnapshot(Base):
    """Calculated point-in-time SLI and error budget snapshot."""

    __tablename__ = "sli_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    slo_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_level_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    good_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_sli_percentage: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    error_budget_remaining_percentage: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    has_sufficient_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    slo: Mapped[ServiceLevelObjective] = relationship("ServiceLevelObjective", back_populates="snapshots")


# =========================================================================
# 6. Automated Rollback Policies & Execution Audit
# =========================================================================


class RollbackPolicy(Base):
    """Governs criteria and behavior for automated or manual slot rollback."""

    __tablename__ = "rollback_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runtime_application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("runtime_applications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    mode: Mapped[RollbackMode] = mapped_column(
        Enum(RollbackMode, native_enum=False), default=RollbackMode.MANUAL_ONLY, nullable=False
    )
    evaluation_window_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    error_rate_threshold_percentage: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    latency_p95_threshold_ms: Mapped[float] = mapped_column(Float, default=2000.0, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    max_automatic_attempts_per_release: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    require_golden_test_pass: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_gate3_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )


class RollbackExecutionEvent(Base):
    """Immutable audit trail for automatic and manual rollback operations."""

    __tablename__ = "rollback_execution_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    runtime_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_slot_name: Mapped[str] = mapped_column(String(16), nullable=False)
    to_slot_name: Mapped[str] = mapped_column(String(16), nullable=False)
    from_model_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    to_model_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    verification_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    golden_test_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 7. Incident Management & Timeline
# =========================================================================


class Incident(Base):
    """Operational incident aggregating alerts, impact, and recovery lifecycle."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    runtime_application_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("runtime_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incident_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, native_enum=False), default=IncidentSeverity.SEV2, nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False), default=IncidentStatus.OPEN, nullable=False, index=True
    )
    primary_alert_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("alert_instances.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list[IncidentEvent]] = relationship(
        "IncidentEvent", back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvent(Base):
    """Chronological event in an incident timeline."""

    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    incident: Mapped[Incident] = relationship("Incident", back_populates="events")
