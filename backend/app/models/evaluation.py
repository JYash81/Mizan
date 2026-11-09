"""SQLAlchemy models for Mizan Milestone 6: Exam & Evaluation Engine."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class EvaluationSuiteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class SuiteVersionStatus(str, enum.Enum):
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


class CaseCategory(str, enum.Enum):
    FACTUAL = "FACTUAL"
    CONCEPTUAL = "CONCEPTUAL"
    PROCEDURAL = "PROCEDURAL"
    COMPARISON = "COMPARISON"
    MULTI_HOP = "MULTI_HOP"
    NUMERICAL = "NUMERICAL"
    DOCUMENT_SPECIFIC = "DOCUMENT_SPECIFIC"
    UNANSWERABLE = "UNANSWERABLE"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    MULTI_HOP = "MULTI_HOP"


class SplitType(str, enum.Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"


class GroundTruthStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ScoringMethod(str, enum.Enum):
    EXACT_MATCH = "EXACT_MATCH"
    TOKEN_F1 = "TOKEN_F1"
    KEYWORD_COVERAGE = "KEYWORD_COVERAGE"
    RETRIEVAL_METRIC = "RETRIEVAL_METRIC"
    CONTEXT_RELEVANCE = "CONTEXT_RELEVANCE"
    GROUNDEDNESS = "GROUNDEDNESS"
    FAITHFULNESS = "FAITHFULNESS"
    CITATION_VERIFICATION = "CITATION_VERIFICATION"
    ABSTENTION = "ABSTENTION"
    SAFETY = "SAFETY"
    COMPLIANCE = "COMPLIANCE"


class EvaluationRunStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EvaluationTargetType(str, enum.Enum):
    RAG_PIPELINE = "RAG_PIPELINE"
    SINGLE_MODEL = "SINGLE_MODEL"
    MOCK_LLM = "MOCK_LLM"
    PROMPT_CONFIG = "PROMPT_CONFIG"
    SUPPLIED_RESPONSES = "SUPPLIED_RESPONSES"


class MetricStatus(str, enum.Enum):
    MEASURED = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class ReviewDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    FLAGGED = "FLAGGED"


class EvaluationSuite(Base):
    """Collection of examination cases bound to a Gate 1 approved business dataset."""

    __tablename__ = "evaluation_suites"

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
    domain: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    source_dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    source_dataset_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )
    gate1_approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gate1_approvals.id", ondelete="SET NULL"), nullable=True
    )

    generation_method: Mapped[str] = mapped_column(String(64), nullable=False, default="rule_based")
    status: Mapped[EvaluationSuiteStatus] = mapped_column(
        Enum(EvaluationSuiteStatus, native_enum=False),
        nullable=False,
        default=EvaluationSuiteStatus.DRAFT,
    )

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )


class EvaluationSuiteVersion(Base):
    """Immutable, reproducible snapshot of an EvaluationSuite and its reviewed cases."""

    __tablename__ = "evaluation_suite_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    suite_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rubric_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rubric_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    source_dataset_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_dataset_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gate1_approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    generation_config_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[SuiteVersionStatus] = mapped_column(
        Enum(SuiteVersionStatus, native_enum=False),
        nullable=False,
        default=SuiteVersionStatus.FINALIZED,
    )

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class EvaluationCase(Base):
    """An individual examination question, candidate reference answer, and source evidence."""

    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_suite_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    case_type: Mapped[str] = mapped_column(String(64), nullable=False, default="standard")
    category: Mapped[CaseCategory] = mapped_column(
        Enum(CaseCategory, native_enum=False), nullable=False, default=CaseCategory.FACTUAL
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, native_enum=False), nullable=False, default=DifficultyLevel.MEDIUM
    )
    split: Mapped[SplitType] = mapped_column(
        Enum(SplitType, native_enum=False), nullable=False, default=SplitType.DEVELOPMENT
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_unanswerable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_document_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_chunk_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_offsets_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    ground_truth_status: Mapped[GroundTruthStatus] = mapped_column(
        Enum(GroundTruthStatus, native_enum=False),
        nullable=False,
        default=GroundTruthStatus.GENERATED,
    )
    generation_method: Mapped[str] = mapped_column(String(64), nullable=False, default="rule_based")
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )


class EvaluationRubric(Base):
    """Rubric profile defining multi-dimensional evaluation criteria and weights."""

    __tablename__ = "evaluation_rubrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class RubricCriterion(Base):
    """Individual criterion within an evaluation rubric."""

    __tablename__ = "rubric_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    rubric_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_rubrics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterion_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_method: Mapped[ScoringMethod] = mapped_column(
        Enum(ScoringMethod, native_enum=False), nullable=False, default=ScoringMethod.EXACT_MATCH
    )
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    minimum_acceptable_score: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class EvaluationRun(Base):
    """Single execution of an evaluation suite version against a target system."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suite_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_suite_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    rubric_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rubric_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    target_type: Mapped[EvaluationTargetType] = mapped_column(
        Enum(EvaluationTargetType, native_enum=False),
        nullable=False,
        default=EvaluationTargetType.RAG_PIPELINE,
    )
    target_name: Mapped[str] = mapped_column(String(255), nullable=False, default="default-rag")
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False, default="mock")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="mock-gpt-mizan-v1")
    retrieval_config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    status: Mapped[EvaluationRunStatus] = mapped_column(
        Enum(EvaluationRunStatus, native_enum=False),
        nullable=False,
        default=EvaluationRunStatus.DRAFT,
    )
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class EvaluationCaseResult(Base):
    """Result of evaluating an individual examination case in a run."""

    __tablename__ = "evaluation_case_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    actual_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_answer_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall_case_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")

    retrieved_chunks_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    citations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class EvaluationMetricResult(Base):
    """Result of evaluating an individual metric on a case result."""

    __tablename__ = "evaluation_metric_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    case_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_case_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score_scale: Mapped[str] = mapped_column(String(32), nullable=False, default="0-100")
    status: Mapped[MetricStatus] = mapped_column(
        Enum(MetricStatus, native_enum=False), nullable=False, default=MetricStatus.MEASURED
    )
    evaluator_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )


class EvaluationReview(Base):
    """Audit log of human review decisions on examination cases."""

    __tablename__ = "evaluation_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, native_enum=False), nullable=False
    )
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
