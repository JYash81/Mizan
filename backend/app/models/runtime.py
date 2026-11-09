"""SQLAlchemy models for Milestone 13: Customer Runtime, Site Agent, Blue/Green Slots, and Golden Tests."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SiteStatus(str, enum.Enum):
    """Operational lifecycle state of a Customer Site."""

    ENROLLING = "ENROLLING"
    ACTIVE = "ACTIVE"
    OFFLINE = "OFFLINE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class AgentIdentityStatus(str, enum.Enum):
    """Cryptographic status of an enrolled Site Agent."""

    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    REVOKED = "REVOKED"


class RuntimeAppStatus(str, enum.Enum):
    """Installation state of an application package on a Customer Site."""

    INSTALLED = "INSTALLED"
    UPGRADING = "UPGRADING"
    ERROR = "ERROR"
    UNINSTALLED = "UNINSTALLED"


class SlotName(str, enum.Enum):
    """Designation for Blue/Green runtime slots."""

    SLOT_A = "SLOT_A"
    SLOT_B = "SLOT_B"


class SlotStatus(str, enum.Enum):
    """Lifecycle state of an individual runtime deployment slot."""

    EMPTY = "EMPTY"
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ReadinessState(str, enum.Enum):
    """Traffic serving readiness of a runtime slot."""

    UNINITIALIZED = "UNINITIALIZED"
    LOADING = "LOADING"
    READY = "READY"
    UNHEALTHY = "UNHEALTHY"


class GoldenTestOutcome(str, enum.Enum):
    """Outcome of a golden test run or individual test case."""

    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"


class AgentCommandType(str, enum.Enum):
    """Allowlisted, typed commands permitted for Site Agent execution."""

    FETCH_APPROVED_PACKAGE = "FETCH_APPROVED_PACKAGE"
    VERIFY_PACKAGE = "VERIFY_PACKAGE"
    STAGE_PACKAGE = "STAGE_PACKAGE"
    REPORT_RUNTIME_STATUS = "REPORT_RUNTIME_STATUS"
    REQUEST_GOLDEN_TEST = "REQUEST_GOLDEN_TEST"
    SYNC_APPROVED_METADATA = "SYNC_APPROVED_METADATA"


class AgentCommandStatus(str, enum.Enum):
    """Lifecycle of a dispatched Site Agent command."""

    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


# =========================================================================
# 1. Customer Site & Agent Identity
# =========================================================================


class CustomerSite(Base):
    """A registered customer-owned deployment environment (on-prem, edge, customer cloud)."""

    __tablename__ = "customer_sites"
    __table_args__ = (
        UniqueConstraint("workspace_id", "site_key", name="uq_site_workspace_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_key: Mapped[str] = mapped_column(String(100), nullable=False)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[SiteStatus] = mapped_column(
        Enum(SiteStatus, native_enum=False), default=SiteStatus.ENROLLING, nullable=False, index=True
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

    # Relationships
    agent_identity: Mapped[SiteAgentIdentity | None] = relationship(
        "SiteAgentIdentity", back_populates="site", uselist=False, cascade="all, delete-orphan"
    )
    enrollment_tokens: Mapped[list[SiteEnrollmentToken]] = relationship(
        "SiteEnrollmentToken", back_populates="site", cascade="all, delete-orphan"
    )
    installed_applications: Mapped[list[RuntimeApplication]] = relationship(
        "RuntimeApplication", back_populates="site", cascade="all, delete-orphan"
    )
    commands: Mapped[list[SiteAgentCommand]] = relationship(
        "SiteAgentCommand", back_populates="site", cascade="all, delete-orphan"
    )
    telemetry_configuration: Mapped[Any] = relationship(
        "TelemetryConfiguration", uselist=False, cascade="all, delete-orphan"
    )


class SiteEnrollmentToken(Base):
    """High-entropy, single-use token for securely enrolling a Site Agent."""

    __tablename__ = "site_enrollment_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    site: Mapped[CustomerSite] = relationship("CustomerSite", back_populates="enrollment_tokens")


class SiteAgentIdentity(Base):
    """Enrolled Site Agent cryptographic identity. Private keys remain at customer site."""

    __tablename__ = "site_agent_identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(36), default=_id, unique=True, nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)

    status: Mapped[AgentIdentityStatus] = mapped_column(
        Enum(AgentIdentityStatus, native_enum=False), default=AgentIdentityStatus.ACTIVE, nullable=False
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runtime_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform_info_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    site: Mapped[CustomerSite] = relationship("CustomerSite", back_populates="agent_identity")

    @property
    def platform_info(self) -> dict[str, Any]:
        try:
            return json.loads(self.platform_info_json)
        except Exception:
            return {}


# =========================================================================
# 2. Installed Applications & Blue/Green Slots
# =========================================================================


class RuntimeApplication(Base):
    """An application package installed and operating at a Customer Site."""

    __tablename__ = "runtime_applications"
    __table_args__ = (
        UniqueConstraint("customer_site_id", "app_definition_id", name="uq_site_app_def"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_definitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    app_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    app_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    active_slot_name: Mapped[str] = mapped_column(String(16), default="SLOT_A", nullable=False)

    status: Mapped[RuntimeAppStatus] = mapped_column(
        Enum(RuntimeAppStatus, native_enum=False), default=RuntimeAppStatus.INSTALLED, nullable=False
    )

    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
    )

    site: Mapped[CustomerSite] = relationship("CustomerSite", back_populates="installed_applications")
    slots: Mapped[list[RuntimeSlot]] = relationship(
        "RuntimeSlot", back_populates="application", cascade="all, delete-orphan"
    )


class RuntimeSlot(Base):
    """A Blue or Green deployment slot managing loaded model/app configurations."""

    __tablename__ = "runtime_slots"
    __table_args__ = (
        UniqueConstraint("runtime_application_id", "slot_name", name="uq_app_slot_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    runtime_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_name: Mapped[SlotName] = mapped_column(
        Enum(SlotName, native_enum=False), default=SlotName.SLOT_A, nullable=False
    )

    app_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("app_versions.id", ondelete="SET NULL"), nullable=True
    )
    model_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True
    )
    release_manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, native_enum=False), default=SlotStatus.EMPTY, nullable=False, index=True
    )
    readiness_state: Mapped[ReadinessState] = mapped_column(
        Enum(ReadinessState, native_enum=False), default=ReadinessState.UNINITIALIZED, nullable=False
    )
    golden_test_status: Mapped[GoldenTestOutcome] = mapped_column(
        Enum(GoldenTestOutcome, native_enum=False), default=GoldenTestOutcome.NOT_RUN, nullable=False
    )

    last_golden_test_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    engine_adapter_key: Mapped[str] = mapped_column(String(64), default="MOCK_ENGINE", nullable=False)
    configuration_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    staged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    application: Mapped[RuntimeApplication] = relationship("RuntimeApplication", back_populates="slots")
    golden_test_runs: Mapped[list[GoldenTestRun]] = relationship(
        "GoldenTestRun", back_populates="slot", cascade="all, delete-orphan"
    )

    @property
    def configuration_snapshot(self) -> dict[str, Any]:
        try:
            return json.loads(self.configuration_snapshot_json)
        except Exception:
            return {}


# =========================================================================
# 3. Golden Test Runner & Results
# =========================================================================


class GoldenTestSuite(Base):
    """Versioned suite of acceptance tests bound to an application and model release."""

    __tablename__ = "golden_test_suites"
    __table_args__ = (
        UniqueConstraint("app_version_id", "suite_version", name="uq_app_suite_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    app_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    suite_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Serialized test cases list: startup, inference smoke, schema, RAG citations, safety, offline path
    cases_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    runs: Mapped[list[GoldenTestRun]] = relationship("GoldenTestRun", back_populates="suite")

    @property
    def cases(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.cases_json)
        except Exception:
            return []


class GoldenTestRun(Base):
    """Execution record of a Golden Test Suite against a candidate runtime slot."""

    __tablename__ = "golden_test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    runtime_slot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_slots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("golden_test_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_version: Mapped[str] = mapped_column(String(64), default="1.0.0", nullable=False)

    outcome: Mapped[GoldenTestOutcome] = mapped_column(
        Enum(GoldenTestOutcome, native_enum=False), default=GoldenTestOutcome.NOT_RUN, nullable=False, index=True
    )
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Privacy-safe execution summary (NO customer prompts logged)
    results_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slot: Mapped[RuntimeSlot] = relationship("RuntimeSlot", back_populates="golden_test_runs")
    suite: Mapped[GoldenTestSuite] = relationship("GoldenTestSuite", back_populates="runs")

    @property
    def results_summary(self) -> dict[str, Any]:
        try:
            return json.loads(self.results_summary_json)
        except Exception:
            return {}


# =========================================================================
# 4. Outbound Signed Commands & Activation Audit
# =========================================================================


class SiteAgentCommand(Base):
    """Signed, typed, allowlisted command polled outbound by a Site Agent."""

    __tablename__ = "site_agent_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command_id: Mapped[str] = mapped_column(String(36), default=_id, unique=True, nullable=False)
    command_type: Mapped[AgentCommandType] = mapped_column(
        Enum(AgentCommandType, native_enum=False), nullable=False, index=True
    )

    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signature: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[AgentCommandStatus] = mapped_column(
        Enum(AgentCommandStatus, native_enum=False), default=AgentCommandStatus.PENDING, nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped[CustomerSite] = relationship("CustomerSite", back_populates="commands")

    @property
    def payload(self) -> dict[str, Any]:
        try:
            return json.loads(self.payload_json)
        except Exception:
            return {}


class RuntimeActivationEvent(Base):
    """Append-only audit record of runtime slot activation and manual slot switching."""

    __tablename__ = "runtime_activation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    customer_site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customer_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    runtime_application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runtime_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    previous_slot_name: Mapped[str] = mapped_column(String(16), nullable=False)
    new_slot_name: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    app_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    release_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    golden_test_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    switch_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
