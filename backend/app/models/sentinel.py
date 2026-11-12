"""SQLAlchemy models for Sentinel v2 & Security Governance.

Implements the Mizan Security Strategy v2:
- Three-part Sentinel: Detect, Decide, Act Enforcer.
- Signed, scoped, single-tenant containment orders with replay-resistant nonces.
- JIT Support Access Broker with dual approval for restricted data and customer-visible session audits.
- Sealed Evidence Vault with two-person release workflow and retention auto-purge.
- Signed minimum-version floor for anti-rollback protection.
- Regulatory incident clocks (GDPR 72-hour window and contractual notification SLAs).
- Two-person Sev1 recovery workflow.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
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


class ContainmentTargetType(str, enum.Enum):
    """Scoped targets for Sentinel containment orders."""

    AGENT_RUN = "AGENT_RUN"
    TOKEN = "TOKEN"
    SESSION = "SESSION"
    CUSTOMER_SITE = "CUSTOMER_SITE"
    RUNTIME_SLOT = "RUNTIME_SLOT"
    SERVICE = "SERVICE"


class ContainmentAction(str, enum.Enum):
    """Action executed by local runtime enforcers."""

    ISOLATE_AGENT = "ISOLATE_AGENT"
    REVOKE_TOKEN = "REVOKE_TOKEN"
    TERMINATE_SESSION = "TERMINATE_SESSION"
    QUARANTINE_SLOT = "QUARANTINE_SLOT"
    SUSPEND_SITE = "SUSPEND_SITE"
    CONTAIN_SERVICE = "CONTAIN_SERVICE"


class OrderExecutionStatus(str, enum.Enum):
    """Status of a signed containment order."""

    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class SupportAccessScope(str, enum.Enum):
    """Permissions requested by support staff through the broker."""

    DIAGNOSTICS_READ = "DIAGNOSTICS_READ"
    CONFIG_AUDIT = "CONFIG_AUDIT"
    METRICS_INSPECT = "METRICS_INSPECT"
    RESTRICTED_DATA_DEBUG = "RESTRICTED_DATA_DEBUG"


class SupportAccessStatus(str, enum.Enum):
    """Lifecycle of a just-in-time support access request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class SealedEvidenceStatus(str, enum.Enum):
    """Lifecycle of encrypted sealed evidence in forensic escrow."""

    SEALED = "SEALED"
    RELEASED = "RELEASED"
    PURGED = "PURGED"


# =========================================================================
# 1. Sentinel Containment Orders & Enforcer Tracking
# =========================================================================


class SentinelContainmentOrder(Base):
    """Short-lived, cryptographically signed, single-tenant containment order."""

    __tablename__ = "sentinel_containment_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[ContainmentTargetType] = mapped_column(
        Enum(ContainmentTargetType, native_enum=False), nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[ContainmentAction] = mapped_column(
        Enum(ContainmentAction, native_enum=False), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    is_cross_tenant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dual_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approver_1_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_2_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    signature: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_payload: Mapped[str] = mapped_column(Text, default="", nullable=False)
    signature_purpose: Mapped[str] = mapped_column(
        String(64), default="SENTINEL_CONTAINMENT_ORDER", nullable=False
    )
    signer_key_id: Mapped[str] = mapped_column(
        String(64), default="sentinel_decide_key", nullable=False
    )

    execution_status: Mapped[OrderExecutionStatus] = mapped_column(
        Enum(OrderExecutionStatus, native_enum=False),
        default=OrderExecutionStatus.PENDING,
        nullable=False,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by_enforcer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


class ExecutedNonce(Base):
    """Replay prevention ledger for containment orders."""

    __tablename__ = "sentinel_executed_nonces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    nonce: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 2. Support Access Broker (No Standing Access)
# =========================================================================


class SupportAccessRequest(Base):
    """Customer-approved just-in-time support credential broker."""

    __tablename__ = "support_access_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_staff_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requested_scope: Mapped[SupportAccessScope] = mapped_column(
        Enum(SupportAccessScope, native_enum=False), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[SupportAccessStatus] = mapped_column(
        Enum(SupportAccessStatus, native_enum=False),
        default=SupportAccessStatus.PENDING,
        nullable=False,
    )

    approved_by_customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    second_approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    second_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    token_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_break_glass: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    break_glass_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    session_logs: Mapped[list[SupportSessionLog]] = relationship(
        "SupportSessionLog", back_populates="request", cascade="all, delete-orphan"
    )


class SupportSessionLog(Base):
    """Customer-auditable real-time session logs for JIT support access."""

    __tablename__ = "support_session_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    access_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("support_access_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    staff_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    request_method: Mapped[str] = mapped_column(String(16), default="GET", nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    request: Mapped[SupportAccessRequest] = relationship(
        "SupportAccessRequest", back_populates="session_logs"
    )


# =========================================================================
# 3. Sealed Evidence Vault (Two-Person Release & Auto-Purge)
# =========================================================================


class SealedEvidenceRecord(Base):
    """Forensic evidence encrypted under a dedicated key requiring dual approval."""

    __tablename__ = "sealed_evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(64), default="application/json", nullable=False
    )
    encryption_key_id: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[SealedEvidenceStatus] = mapped_column(
        Enum(SealedEvidenceStatus, native_enum=False),
        default=SealedEvidenceStatus.SEALED,
        nullable=False,
    )
    release_approver_1_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    release_approver_2_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 4. Anti-Rollback Signed Minimum-Version Floor
# =========================================================================


class SignedVersionFloor(Base):
    """Cryptographically signed minimum acceptable version floor to stop downgrades."""

    __tablename__ = "signed_version_floors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    minimum_version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_payload: Mapped[str] = mapped_column(Text, default="", nullable=False)
    signer_public_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 5. Regulatory Incident Clocks (GDPR 72h & Contractual SLAs)
# =========================================================================


class IncidentRegulatoryClock(Base):
    """Tracks regulatory and contractual notification deadlines from time of awareness."""

    __tablename__ = "incident_regulatory_clocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    awareness_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    gdpr_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    customer_contract_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    gdpr_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customer_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


# =========================================================================
# 6. Sev1 Two-Person Recovery Record
# =========================================================================


class Sev1RecoveryRecord(Base):
    """Mandatory dual-authorization workflow for restoring Sev1 contained services."""

    __tablename__ = "sev1_recovery_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    triggering_actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    approver_1_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_1_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approver_2_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_2_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    integrity_check_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    integrity_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
