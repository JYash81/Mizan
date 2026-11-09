"""SQLAlchemy models for Mizan Milestone 9: Recommendation Engine & Multi-Objective Optimization."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class RecommendationRunStatus(str, enum.Enum):
    """Lifecycle status of a recommendation run."""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class CandidateProvenanceStatus(str, enum.Enum):
    """Provenance verification status for a candidate configuration."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    INCOMPATIBLE = "INCOMPATIBLE"
    INCOMPLETE = "INCOMPLETE"
    EXCLUDED = "EXCLUDED"


class CandidateEligibilityStatus(str, enum.Enum):
    """Eligibility status after hard constraint filtering."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RecommendationDecisionType(str, enum.Enum):
    """Human decision recorded on a recommendation outcome."""

    ACCEPTED_FOR_FURTHER_REVIEW = "ACCEPTED_FOR_FURTHER_REVIEW"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"


class RecommendationRun(Base):
    """Execution container and snapshot for multi-objective optimization and recommendation."""

    __tablename__ = "recommendation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecommendationRunStatus] = mapped_column(
        Enum(RecommendationRunStatus), default=RecommendationRunStatus.DRAFT, nullable=False, index=True
    )

    algorithm_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Input & Normalization Snapshots (Canonical JSON RFC 8785 for exact reproducibility)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    normalization_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    weights_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Summary KPIs
    total_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    eligible_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frontier_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    candidates: Mapped[list[RecommendationCandidate]] = relationship(
        "RecommendationCandidate",
        back_populates="recommendation_run",
        cascade="all, delete-orphan",
        order_by="RecommendationCandidate.created_at",
    )
    scenarios: Mapped[list[RecommendationScenario]] = relationship(
        "RecommendationScenario",
        back_populates="recommendation_run",
        cascade="all, delete-orphan",
    )
    decisions: Mapped[list[RecommendationDecision]] = relationship(
        "RecommendationDecision",
        back_populates="recommendation_run",
        cascade="all, delete-orphan",
        order_by="RecommendationDecision.created_at",
    )
    events: Mapped[list[RecommendationEvent]] = relationship(
        "RecommendationEvent",
        back_populates="recommendation_run",
        cascade="all, delete-orphan",
        order_by="RecommendationEvent.created_at",
    )


class RecommendationCandidate(Base):
    """Candidate configuration evaluated within a recommendation run."""

    __tablename__ = "recommendation_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recommendation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experiment_trial_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiment_trials.id", ondelete="CASCADE"), nullable=False, index=True
    )

    candidate_label: Mapped[str] = mapped_column(String(255), nullable=False)
    configuration_digest: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance linkages
    evaluation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluation_suite_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluation_suite_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluation_split: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hardware_profile_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Status & Outcomes
    provenance_status: Mapped[CandidateProvenanceStatus] = mapped_column(
        Enum(CandidateProvenanceStatus), default=CandidateProvenanceStatus.VERIFIED, nullable=False
    )
    eligibility_status: Mapped[CandidateEligibilityStatus] = mapped_column(
        Enum(CandidateEligibilityStatus), default=CandidateEligibilityStatus.ELIGIBLE, nullable=False
    )
    exclusion_reasons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Extracted raw and normalized metrics
    objective_values_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    normalized_objective_values_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    constraint_results_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    # Multi-Objective Optimization Results
    pareto_frontier_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    dominated_by_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    dominates_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    weighted_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Evidence breakdown by objective (MEASURED, ESTIMATED, UNAVAILABLE, etc.)
    evidence_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    recommendation_run: Mapped[RecommendationRun] = relationship(
        "RecommendationRun", back_populates="candidates"
    )

    @property
    def objective_values(self) -> dict[str, Any]:
        if not self.objective_values_json:
            return {}
        try:
            return json.loads(self.objective_values_json)
        except Exception:
            return {}

    @property
    def normalized_objective_values(self) -> dict[str, float]:
        if not self.normalized_objective_values_json:
            return {}
        try:
            return json.loads(self.normalized_objective_values_json)
        except Exception:
            return {}


class OptimizationProfile(Base):
    """User-configured preference profile and optimization objectives for a workspace."""

    __tablename__ = "optimization_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_optimization_profile_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    objectives_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    weights_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    constraints_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    preferred_hardware_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False
    )


class RecommendationScenario(Base):
    """Alternative weighted scoring scenario or sensitivity perturbation for a recommendation run."""

    __tablename__ = "recommendation_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recommendation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    weight_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    ranking_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    recommendation_run: Mapped[RecommendationRun] = relationship(
        "RecommendationRun", back_populates="scenarios"
    )

    @property
    def weight_snapshot(self) -> dict[str, float]:
        if not self.weight_snapshot_json:
            return {}
        try:
            return json.loads(self.weight_snapshot_json)
        except Exception:
            return {}

    @property
    def ranking_snapshot(self) -> Any:
        if not self.ranking_snapshot_json:
            return None
        try:
            return json.loads(self.ranking_snapshot_json)
        except Exception:
            return None


class RecommendationDecision(Base):
    """Auditable human review decision recorded on an evaluated candidate or run."""

    __tablename__ = "recommendation_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recommendation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_candidate_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recommendation_candidates.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[RecommendationDecisionType] = mapped_column(
        Enum(RecommendationDecisionType), nullable=False, index=True
    )
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    recommendation_run: Mapped[RecommendationRun] = relationship(
        "RecommendationRun", back_populates="decisions"
    )


class RecommendationEvent(Base):
    """Immutable audit trail of lifecycle events within a recommendation run."""

    __tablename__ = "recommendation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recommendation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    recommendation_run: Mapped[RecommendationRun] = relationship(
        "RecommendationRun", back_populates="events"
    )
