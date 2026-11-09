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


class MaskingRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    MASKING = "MASKING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExtractionCoverage(str, enum.Enum):
    EXTRACTION_COMPLETE = "EXTRACTION_COMPLETE"
    PARTIALLY_EXTRACTED = "PARTIALLY_EXTRACTED"
    OCR_REQUIRED = "OCR_REQUIRED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXCLUDED_BY_AUTHORIZED_REVIEWER = "EXCLUDED_BY_AUTHORIZED_REVIEWER"


class FindingStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    MANUAL = "MANUAL"


class DecisionType(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    MANUALLY_ADDED = "MANUALLY_ADDED"
    SPAN_CORRECTED = "SPAN_CORRECTED"
    REPLACEMENT_CHANGED = "REPLACEMENT_CHANGED"


class Gate1Decision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INVALIDATED = "INVALIDATED"


class MaskingStrategy(str, enum.Enum):
    REPLACE_WITH_ENTITY_LABEL = "REPLACE_WITH_ENTITY_LABEL"
    REDACT = "REDACT"
    PARTIAL_MASK = "PARTIAL_MASK"


MASKING_RUN_STATUS = Enum(
    MaskingRunStatus,
    native_enum=False,
    create_constraint=True,
    name="masking_run_status",
)
EXTRACTION_COVERAGE = Enum(
    ExtractionCoverage,
    native_enum=False,
    create_constraint=True,
    name="extraction_coverage",
)
FINDING_STATUS = Enum(
    FindingStatus,
    native_enum=False,
    create_constraint=True,
    name="finding_status",
)
DECISION_TYPE = Enum(
    DecisionType,
    native_enum=False,
    create_constraint=True,
    name="decision_type",
)
GATE1_DECISION = Enum(
    Gate1Decision,
    native_enum=False,
    create_constraint=True,
    name="gate1_decision",
)
MASKING_STRATEGY = Enum(
    MaskingStrategy,
    native_enum=False,
    create_constraint=True,
    name="masking_strategy",
)


class MaskingProfile(Base):
    __tablename__ = "masking_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en")
    enabled_entities_json: Mapped[str] = mapped_column(Text)
    replacement_strategy: Mapped[MaskingStrategy] = mapped_column(
        MASKING_STRATEGY, default=MaskingStrategy.REPLACE_WITH_ENTITY_LABEL
    )
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MaskingRun(Base):
    __tablename__ = "masking_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    source_dataset_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    masking_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("masking_profiles.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[MaskingRunStatus] = mapped_column(
        MASKING_RUN_STATUS, default=MaskingRunStatus.PENDING, index=True
    )
    extraction_coverage: Mapped[ExtractionCoverage] = mapped_column(
        EXTRACTION_COVERAGE, default=ExtractionCoverage.EXTRACTION_COMPLETE
    )
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    documents_failed: Mapped[int] = mapped_column(Integer, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    masked_output_digest: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PiiFinding(Base):
    __tablename__ = "pii_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    masking_run_id: Mapped[str] = mapped_column(
        ForeignKey("masking_runs.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    recognizer_name: Mapped[str] = mapped_column(String(120))
    recognizer_version: Mapped[str] = mapped_column(String(32), default="1.0")
    detection_score: Mapped[float] = mapped_column(Float)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    offset_unit: Mapped[str] = mapped_column(String(32), default="unicode_codepoint")
    page_number: Mapped[int | None] = mapped_column(Integer)
    overlap_group_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[FindingStatus] = mapped_column(
        FINDING_STATUS, default=FindingStatus.DETECTED, index=True
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MaskingDecision(Base):
    __tablename__ = "masking_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    masking_run_id: Mapped[str] = mapped_column(
        ForeignKey("masking_runs.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[str] = mapped_column(
        ForeignKey("pii_findings.id", ondelete="CASCADE"), index=True
    )
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision_type: Mapped[DecisionType] = mapped_column(DECISION_TYPE)
    reason: Mapped[str | None] = mapped_column(Text)
    custom_replacement: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Gate1Approval(Base):
    __tablename__ = "gate1_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    masking_run_id: Mapped[str] = mapped_column(
        ForeignKey("masking_runs.id", ondelete="CASCADE"), index=True
    )
    source_dataset_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    masked_output_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    findings_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reviewer_role_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[Gate1Decision] = mapped_column(
        GATE1_DECISION, default=Gate1Decision.APPROVED, index=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text)
    signature_algorithm: Mapped[str] = mapped_column(String(32), default="Ed25519")
    signing_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_signature: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_payload: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Gate1ApprovalEvent(Base):
    __tablename__ = "gate1_approval_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    approval_id: Mapped[str] = mapped_column(
        ForeignKey("gate1_approvals.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
