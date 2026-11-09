"""SQLAlchemy models for Mizan Milestone 7: Model Experimentation & Trial Matrix Engine."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime
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
from app.models.evaluation import SplitType


def _id() -> str:
    return str(uuid.uuid4())


class ExperimentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class TrialStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class Experiment(Base):
    """Container for controlled model and configuration experimentation."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False, index=True
    )

    # Dataset & Gate 1 Provenance
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gate1_approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Evaluation Suite & Split
    evaluation_suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_suite_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suite_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    canonical_suite_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evaluation_split: Mapped[SplitType] = mapped_column(
        Enum(SplitType), default=SplitType.VALIDATION, nullable=False
    )

    # Baseline & Matrix Configuration
    baseline_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Execution Progress & Stats
    total_trials: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_trials: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_trials: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_trials: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps & Lifecycle
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False
    )

    # Relationships
    trials: Mapped[list[ExperimentTrial]] = relationship(
        "ExperimentTrial",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentTrial.trial_number",
    )
    events: Mapped[list[ExperimentEvent]] = relationship(
        "ExperimentEvent",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="ExperimentEvent.created_at",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_experiment_slug"),
    )


class ExperimentTrial(Base):
    """Single controlled configuration trial within an experiment."""

    __tablename__ = "experiment_trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus), default=TrialStatus.PENDING, nullable=False, index=True
    )

    # Trial Parameters & Digest
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_digest: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # M6 Evaluation Linkage & Comparable Results
    evaluation_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    aggregate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Observed Execution Latencies (from M6 Runtime)
    latency_p50_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_p99_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Diagnostics & Retries
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False
    )

    # Relationships
    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="trials")

    @property
    def configuration(self) -> dict[str, Any]:
        """Parsed configuration dictionary."""
        if not self.configuration_json:
            return {}
        try:
            return json.loads(self.configuration_json)
        except Exception:
            return {}

    __table_args__ = (
        UniqueConstraint("experiment_id", "trial_number", name="uq_experiment_trial_number"),
    )


class ExperimentEvent(Base):
    """Audit log entry for experiment lifecycle transitions and trial execution events."""

    __tablename__ = "experiment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trial_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("experiment_trials.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="events")
