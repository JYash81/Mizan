"""SQLAlchemy models for Milestone 11: Artifact Registry, Model Versioning, Release Manifests, and Gate 3 Approval."""

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


class ModelFamilyStatus(str, enum.Enum):
    """Lifecycle status of a Model Family."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ModelVersionStatus(str, enum.Enum):
    """Lifecycle and release state of a Model Version."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class RegisteredArtifactType(str, enum.Enum):
    """Artifact type stored in the immutable Artifact Registry."""

    BASE_WEIGHTS = "BASE_WEIGHTS"
    LORA_ADAPTER = "LORA_ADAPTER"
    QLORA_ADAPTER = "QLORA_ADAPTER"
    MERGED_WEIGHTS = "MERGED_WEIGHTS"
    GGUF_FP16 = "GGUF_FP16"
    GGUF_Q8_0 = "GGUF_Q8_0"
    GGUF_Q4_K_M = "GGUF_Q4_K_M"
    AWQ_QUANTIZED = "AWQ_QUANTIZED"
    TOKENIZER_PACKAGE = "TOKENIZER_PACKAGE"
    BUILD_REPORT = "BUILD_REPORT"
    CONFIG = "CONFIG"
    EVALUATION_REPORT = "EVALUATION_REPORT"
    TRAINING_MANIFEST = "TRAINING_MANIFEST"


class Gate3Decision(str, enum.Enum):
    """Human decision taken during Gate 3 release review."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class ModelFamily(Base):
    """Organization/workspace-scoped collection of related model versions."""

    __tablename__ = "model_families"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_model_family_workspace_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), default="TEXT_GENERATION", nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ModelFamilyStatus] = mapped_column(
        Enum(ModelFamilyStatus, native_enum=False), default=ModelFamilyStatus.ACTIVE, nullable=False
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

    versions: Mapped[list[ModelVersion]] = relationship(
        "ModelVersion", back_populates="family", cascade="all, delete-orphan", order_by="desc(ModelVersion.created_at)"
    )


class ModelVersion(Base):
    """An immutable, versioned model release candidate or approved release package."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("family_id", "version_tag", name="uq_model_version_family_tag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ModelVersionStatus] = mapped_column(
        Enum(ModelVersionStatus, native_enum=False), default=ModelVersionStatus.DRAFT, nullable=False, index=True
    )

    # Lineage & Provenance References
    build_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_build_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_model_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_model_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    recipe_key: Mapped[str] = mapped_column(String(64), nullable=False)

    dataset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )
    dataset_version_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gate1_approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gate1_approvals.id", ondelete="SET NULL"), nullable=True
    )

    # Evaluation Evidence
    base_evaluation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_evaluation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Hardware & Memory Feasibility
    min_ram_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    min_vram_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_hardware_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Cryptographic Release Manifest & Provenance
    release_manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provenance_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

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

    family: Mapped[ModelFamily] = relationship("ModelFamily", back_populates="versions")
    artifacts: Mapped[list[RegisteredArtifact]] = relationship(
        "RegisteredArtifact", back_populates="model_version", cascade="all, delete-orphan"
    )
    gate3_approval: Mapped[Gate3Approval | None] = relationship(
        "Gate3Approval", back_populates="model_version", uselist=False, cascade="all, delete-orphan"
    )
    revocations: Mapped[list[Gate3Revocation]] = relationship(
        "Gate3Revocation", back_populates="model_version", cascade="all, delete-orphan"
    )
    release_events: Mapped[list[ModelReleaseEvent]] = relationship(
        "ModelReleaseEvent", back_populates="model_version", cascade="all, delete-orphan", order_by="desc(ModelReleaseEvent.created_at)"
    )

    @property
    def is_immutable(self) -> bool:
        """Returns True if the release is finalized and approved, preventing mutations."""
        return self.status in {ModelVersionStatus.APPROVED, ModelVersionStatus.REVOKED, ModelVersionStatus.ARCHIVED}

    @property
    def provenance_summary(self) -> dict[str, Any]:
        if not self.provenance_summary_json:
            return {}
        try:
            return json.loads(self.provenance_summary_json)
        except Exception:
            return {}


class RegisteredArtifact(Base):
    """Immutable registered model artifact linked to a Model Version."""

    __tablename__ = "registered_artifacts"
    __table_args__ = (
        UniqueConstraint("model_version_id", "sha256", name="uq_reg_artifact_version_sha"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staged_artifact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("staged_model_artifacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    artifact_type: Mapped[RegisteredArtifactType] = mapped_column(
        Enum(RegisteredArtifactType, native_enum=False), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # SAFETENSORS, GGUF, JSON, etc.
    quantization_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_primary_weights: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="artifacts")


class Gate3Approval(Base):
    """Cryptographic Gate 3 Human Release Approval Attestation."""

    __tablename__ = "gate3_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    release_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)

    decision: Mapped[Gate3Decision] = mapped_column(
        Enum(Gate3Decision, native_enum=False), default=Gate3Decision.APPROVED, nullable=False, index=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_role_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)

    signature_algorithm: Mapped[str] = mapped_column(String(32), default="Ed25519", nullable=False)
    signature_purpose: Mapped[str] = mapped_column(
        String(64), default="GATE3_RELEASE_APPROVAL", nullable=False
    )
    signing_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_signature: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_payload: Mapped[str] = mapped_column(Text, nullable=False)

    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="gate3_approval")
    revocations: Mapped[list[Gate3Revocation]] = relationship(
        "Gate3Revocation", back_populates="gate3_approval", cascade="all, delete-orphan"
    )


class Gate3Revocation(Base):
    """Audit and revocation event for an approved model release."""

    __tablename__ = "gate3_revocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gate3_approval_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gate3_approvals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revoked_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    revoked_by_role_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    revocation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="revocations")
    gate3_approval: Mapped[Gate3Approval] = relationship("Gate3Approval", back_populates="revocations")


class ModelReleaseEvent(Base):
    """Immutable audit trail for release lifecycle transitions."""

    __tablename__ = "model_release_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    triggered_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="release_events")
