"""SQLAlchemy models for Mizan Milestone 10: Model Building, Fine-Tuning, Quantization & Colab Lab."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
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


def _utc_now_naive() -> datetime:
    """Return UTC for SQLite's timezone-naive timestamp columns.

    The model-building schema currently stores `DateTime` values without a
    timezone. Normalizing at this boundary preserves the existing database
    contract while avoiding deprecated `datetime.utcnow()` calls.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class LicenseStatus(str, enum.Enum):
    """Model license verification status."""

    VERIFIED_LICENSE = "VERIFIED_LICENSE"
    RESTRICTED_LICENSE = "RESTRICTED_LICENSE"
    UNKNOWN_LICENSE = "UNKNOWN_LICENSE"
    LICENSE_REVIEW_REQUIRED = "LICENSE_REVIEW_REQUIRED"
    USER_CONFIRMED_RIGHTS = "USER_CONFIRMED_RIGHTS"


class ModelAccessStatus(str, enum.Enum):
    """Access availability of model weights."""

    PUBLIC = "PUBLIC"
    GATED_PENDING = "GATED_PENDING"
    GATED_APPROVED = "GATED_APPROVED"
    RESTRICTED = "RESTRICTED"


class RecipeType(str, enum.Enum):
    """High-level category of model building recipe."""

    SMOKE_TEST = "SMOKE_TEST"
    LORA_FINETUNE = "LORA_FINETUNE"
    QLORA_FINETUNE = "QLORA_FINETUNE"
    GGUF_CONVERT_QUANTIZE = "GGUF_CONVERT_QUANTIZE"
    AWQ_QUANTIZE = "AWQ_QUANTIZE"


class ModelBuildStatus(str, enum.Enum):
    """Lifecycle state machine for a model build run."""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    BLOCKED_BY_RESOURCES = "BLOCKED_BY_RESOURCES"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    INTERRUPTED = "INTERRUPTED"
    RESUMABLE = "RESUMABLE"
    IMPORT_PENDING = "IMPORT_PENDING"
    VERIFYING_OUTPUT = "VERIFYING_OUTPUT"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class ExecutionMode(str, enum.Enum):
    """Execution environment mode for the build."""

    LOCAL_SMOKE_TEST = "LOCAL_SMOKE_TEST"
    MANUAL_COLAB_NOTEBOOK = "MANUAL_COLAB_NOTEBOOK"
    MANUAL_EXTERNAL_RUNTIME = "MANUAL_EXTERNAL_RUNTIME"


class ArtifactType(str, enum.Enum):
    """Type of staged model artifact produced by a build."""

    LORA_ADAPTER = "LORA_ADAPTER"
    MERGED_WEIGHTS = "MERGED_WEIGHTS"
    GGUF_FP16 = "GGUF_FP16"
    GGUF_Q8_0 = "GGUF_Q8_0"
    GGUF_Q4_K_M = "GGUF_Q4_K_M"
    AWQ_QUANTIZED = "AWQ_QUANTIZED"
    TOKENIZER_PACKAGE = "TOKENIZER_PACKAGE"
    BUILD_REPORT = "BUILD_REPORT"


class ArtifactVerificationStatus(str, enum.Enum):
    """Integrity verification status of staged artifacts."""

    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class ModelRole(str, enum.Enum):
    """Role of evaluated model in comparative evaluation."""

    BASE_MODEL = "BASE_MODEL"
    FINE_TUNED_MODEL = "FINE_TUNED_MODEL"
    QUANTIZED_MODEL = "QUANTIZED_MODEL"


class ModelSource(Base):
    """Catalog of verified model architectures, repositories, and licensing provenance."""

    __tablename__ = "model_sources"
    __table_args__ = (
        UniqueConstraint("model_key", "immutable_revision", name="uq_model_source_key_rev"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    model_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_repository: Mapped[str] = mapped_column(String(64), default="huggingface", nullable=False)
    immutable_revision: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    architecture: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parameter_count_millions: Mapped[float] = mapped_column(Float, nullable=False)
    context_length: Mapped[int] = mapped_column(Integer, default=2048, nullable=False)

    tokenizer_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    license_id: Mapped[str] = mapped_column(String(128), nullable=False)
    license_status: Mapped[LicenseStatus] = mapped_column(
        Enum(LicenseStatus), default=LicenseStatus.UNKNOWN_LICENSE, nullable=False
    )
    license_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    commercial_use_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_gated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_status: Mapped[ModelAccessStatus] = mapped_column(
        Enum(ModelAccessStatus), default=ModelAccessStatus.PUBLIC, nullable=False
    )

    requires_custom_code: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    estimated_download_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    source_metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_runs: Mapped[list[ModelBuildRun]] = relationship(
        "ModelBuildRun", back_populates="source_model"
    )

    @property
    def source_metadata(self) -> dict[str, Any]:
        if not self.source_metadata_json:
            return {}
        try:
            return json.loads(self.source_metadata_json)
        except Exception:
            return {}


class ModelBuildRecipe(Base):
    """Versioned recipe definition for model fine-tuning, conversion, and quantization."""

    __tablename__ = "model_build_recipes"
    __table_args__ = (
        UniqueConstraint("recipe_key", "recipe_version", name="uq_recipe_key_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recipe_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recipe_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    recipe_type: Mapped[RecipeType] = mapped_column(Enum(RecipeType), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    supported_architectures_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_runtimes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    configuration_schema_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    default_config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    dependency_lock_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    resource_requirements_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    is_executable_locally: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_runs: Mapped[list[ModelBuildRun]] = relationship(
        "ModelBuildRun", back_populates="recipe"
    )

    @property
    def supported_architectures(self) -> list[str]:
        if not self.supported_architectures_json:
            return []
        try:
            return json.loads(self.supported_architectures_json)
        except Exception:
            return []

    @property
    def dependency_lock(self) -> dict[str, str]:
        if not self.dependency_lock_json:
            return {}
        try:
            return json.loads(self.dependency_lock_json)
        except Exception:
            return {}

    @property
    def default_config(self) -> dict[str, Any]:
        if not self.default_config_json:
            return {}
        try:
            return json.loads(self.default_config_json)
        except Exception:
            return {}


class ExternalProcessingAuthorization(Base):
    """Explicit human authorization for external processing of a masked dataset in Colab Free."""

    __tablename__ = "external_processing_authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_version_digest: Mapped[str] = mapped_column(String(64), nullable=False)

    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_class: Mapped[str] = mapped_column(
        String(64), default="GOOGLE_COLAB_EPHEMERAL_RUNTIME", nullable=False
    )
    authorized_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    authorization_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )


class ModelBuildRun(Base):
    """Execution container and snapshot for model building, fine-tuning, and quantization."""

    __tablename__ = "model_build_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ModelBuildStatus] = mapped_column(
        Enum(ModelBuildStatus), default=ModelBuildStatus.DRAFT, nullable=False, index=True
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        Enum(ExecutionMode), default=ExecutionMode.LOCAL_SMOKE_TEST, nullable=False
    )

    source_model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_revision: Mapped[str] = mapped_column(String(128), nullable=False)

    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_build_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_key: Mapped[str] = mapped_column(String(128), nullable=False)

    # Optional M9 Candidate Linkage
    recommendation_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recommendation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recommendation_candidate_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recommendation_candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Dataset & Approvals
    dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    gate1_approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gate1_approvals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_processing_authorization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("external_processing_authorizations.id", ondelete="SET NULL"), nullable=True
    )

    # Canonical Manifest & Configuration (RFC 8785 JSON)
    training_config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    build_manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    preflight_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    train_partition_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    val_partition_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utc_now_naive,
        onupdate=_utc_now_naive,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source_model: Mapped[ModelSource] = relationship("ModelSource", back_populates="build_runs")
    recipe: Mapped[ModelBuildRecipe] = relationship("ModelBuildRecipe", back_populates="build_runs")
    checkpoints: Mapped[list[ModelBuildCheckpoint]] = relationship(
        "ModelBuildCheckpoint", back_populates="build_run", cascade="all, delete-orphan"
    )
    events: Mapped[list[ModelBuildEvent]] = relationship(
        "ModelBuildEvent", back_populates="build_run", cascade="all, delete-orphan"
    )
    staged_artifacts: Mapped[list[StagedModelArtifact]] = relationship(
        "StagedModelArtifact", back_populates="build_run", cascade="all, delete-orphan"
    )
    evaluation_links: Mapped[list[ModelEvaluationLink]] = relationship(
        "ModelEvaluationLink", back_populates="build_run", cascade="all, delete-orphan"
    )

    @property
    def training_config(self) -> dict[str, Any]:
        if not self.training_config_json:
            return {}
        try:
            return json.loads(self.training_config_json)
        except Exception:
            return {}

    @property
    def build_manifest(self) -> dict[str, Any]:
        if not self.build_manifest_json:
            return {}
        try:
            return json.loads(self.build_manifest_json)
        except Exception:
            return {}

    @property
    def preflight_snapshot(self) -> dict[str, Any]:
        if not self.preflight_snapshot_json:
            return {}
        try:
            return json.loads(self.preflight_snapshot_json)
        except Exception:
            return {}

    @property
    def warnings(self) -> list[str]:
        if not self.warnings_json:
            return []
        try:
            return json.loads(self.warnings_json)
        except Exception:
            return []


class ModelBuildCheckpoint(Base):
    """Periodic training checkpoint with integrity hashes and metrics."""

    __tablename__ = "model_build_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    build_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_build_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkpoint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    epoch: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_run: Mapped[ModelBuildRun] = relationship(
        "ModelBuildRun", back_populates="checkpoints"
    )

    @property
    def metrics(self) -> dict[str, Any]:
        if not self.metrics_json:
            return {}
        try:
            return json.loads(self.metrics_json)
        except Exception:
            return {}


class ModelBuildEvent(Base):
    """Audit log of build lifecycle transitions, preflight checks, and user actions."""

    __tablename__ = "model_build_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    build_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_build_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_run: Mapped[ModelBuildRun] = relationship("ModelBuildRun", back_populates="events")


class StagedModelArtifact(Base):
    """Staged model build artifact waiting for M11 release review.
    
    IMPORTANT: Staged artifacts are NOT release artifacts and do NOT constitute
    Gate 3 release authorization.
    """

    __tablename__ = "staged_model_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    build_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_build_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # GGUF, SAFETENSORS, AWQ, JSON
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    source_model_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_model_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    quantization_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    model_config_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokenizer_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    verification_status: Mapped[ArtifactVerificationStatus] = mapped_column(
        Enum(ArtifactVerificationStatus), default=ArtifactVerificationStatus.PENDING_VERIFICATION, nullable=False
    )
    verification_details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    is_staged_for_m11: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_run: Mapped[ModelBuildRun] = relationship(
        "ModelBuildRun", back_populates="staged_artifacts"
    )
    evaluation_links: Mapped[list[ModelEvaluationLink]] = relationship(
        "ModelEvaluationLink", back_populates="staged_artifact", cascade="all, delete-orphan"
    )

    @property
    def verification_details(self) -> dict[str, Any]:
        if not self.verification_details_json:
            return {}
        try:
            return json.loads(self.verification_details_json)
        except Exception:
            return {}


class ModelEvaluationLink(Base):
    """Comparative link connecting staged model artifacts to frozen M6 evaluation runs."""

    __tablename__ = "model_evaluation_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    build_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_build_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staged_artifact_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("staged_model_artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    model_role: Mapped[ModelRole] = mapped_column(Enum(ModelRole), nullable=False, index=True)
    evaluation_suite_id: Mapped[str] = mapped_column(String(36), nullable=False)
    evaluation_split: Mapped[str] = mapped_column(String(32), nullable=False)  # DEVELOPMENT or VALIDATION, NEVER HOLDOUT
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    quality_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_delta_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_delta_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    comparison_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now_naive, server_default=func.now(), nullable=False
    )

    build_run: Mapped[ModelBuildRun] = relationship(
        "ModelBuildRun", back_populates="evaluation_links"
    )
    staged_artifact: Mapped[StagedModelArtifact] = relationship(
        "StagedModelArtifact", back_populates="evaluation_links"
    )
