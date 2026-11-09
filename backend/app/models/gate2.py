"""SQLAlchemy models for Mizan Milestone 8: Gate 2 Financial Approval & Governance."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class Gate2ApprovalStatus(str, enum.Enum):
    """Lifecycle status of a Gate 2 financial approval request."""

    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    INVALIDATED = "INVALIDATED"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"


class Gate2ApprovalRequest(Base):
    """Explicit, digitally-signed financial approval request for an infrastructure workload."""

    __tablename__ = "gate2_approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requester_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    workload_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Optional linkages to previous Mizan entities
    dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )
    gate1_approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gate1_approvals.id", ondelete="SET NULL"), nullable=True
    )
    experiment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True
    )

    # Workload specifications
    hardware_profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    instance_type: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    max_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)

    # Cost breakdown and budget limit (stored as exact Decimal string representations)
    estimated_compute_cost: Mapped[str] = mapped_column(String(32), nullable=False)
    estimated_storage_cost: Mapped[str] = mapped_column(String(32), nullable=False, default="0.00")
    estimated_total_cost: Mapped[str] = mapped_column(String(32), nullable=False)
    max_authorized_budget: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")

    # Cryptographic attestation and canonical proposal binding
    proposal_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    proposal_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_catalog_version: Mapped[str] = mapped_column(String(32), nullable=False)

    # Decision and digital signature (Ed25519)
    status: Mapped[Gate2ApprovalStatus] = mapped_column(
        Enum(Gate2ApprovalStatus), default=Gate2ApprovalStatus.DRAFT, nullable=False, index=True
    )
    approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approver_role_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    signing_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signed_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    events: Mapped[list[Gate2ApprovalEvent]] = relationship(
        "Gate2ApprovalEvent",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="Gate2ApprovalEvent.created_at",
    )


class Gate2ApprovalEvent(Base):
    """Immutable audit trail for every state transition in a Gate 2 approval request."""

    __tablename__ = "gate2_approval_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    approval_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gate2_approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    approval_request: Mapped[Gate2ApprovalRequest] = relationship(
        "Gate2ApprovalRequest", back_populates="events"
    )
