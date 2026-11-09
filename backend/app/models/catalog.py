"""SQLAlchemy models for Milestone 12: Model Zoo, App Zoo, Enterprise Catalog, and Hardware Badges."""

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


class CatalogVisibility(str, enum.Enum):
    """Visibility scope for catalog listings."""

    PRIVATE = "PRIVATE"
    WORKSPACE = "WORKSPACE"
    ORGANIZATION = "ORGANIZATION"
    PUBLIC = "PUBLIC"


class PublicationStatus(str, enum.Enum):
    """Lifecycle and moderation state of a catalog listing."""

    DRAFT = "DRAFT"
    SUBMITTED_FOR_REVIEW = "SUBMITTED_FOR_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class DistributionStatus(str, enum.Enum):
    """Artifact distribution availability status."""

    DOWNLOADABLE = "DOWNLOADABLE"
    METADATA_ONLY = "METADATA_ONLY"
    RESTRICTED = "RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"


class HardwareCompatibilityBadge(str, enum.Enum):
    """Honest hardware compatibility badge classification."""

    TESTED = "TESTED"
    ESTIMATED = "ESTIMATED"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


class ModelListing(Base):
    """Enterprise catalog entry for an approved M11 Model Version."""

    __tablename__ = "model_listings"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_model_listing_workspace_slug"),
        UniqueConstraint("model_version_id", name="uq_model_listing_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="GENERAL_CHAT", nullable=False, index=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    visibility: Mapped[CatalogVisibility] = mapped_column(
        Enum(CatalogVisibility, native_enum=False), default=CatalogVisibility.WORKSPACE, nullable=False, index=True
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.DRAFT, nullable=False, index=True
    )
    distribution_status: Mapped[DistributionStatus] = mapped_column(
        Enum(DistributionStatus, native_enum=False), default=DistributionStatus.METADATA_ONLY, nullable=False
    )

    # Sanitized immutable public snapshot when published
    public_metadata_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    publication_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    model_version: Mapped[Any] = relationship("ModelVersion", foreign_keys=[model_version_id])
    model_family: Mapped[Any] = relationship("ModelFamily", foreign_keys=[model_family_id])
    hardware_snapshots: Mapped[list[HardwareCompatibilitySnapshot]] = relationship(
        "HardwareCompatibilitySnapshot",
        primaryjoin="and_(HardwareCompatibilitySnapshot.listing_id==ModelListing.id, HardwareCompatibilitySnapshot.listing_type=='MODEL')",
        foreign_keys="HardwareCompatibilitySnapshot.listing_id",
        cascade="all, delete-orphan",
        overlaps="hardware_snapshots",
    )

    @property
    def tags(self) -> list[str]:
        try:
            return json.loads(self.tags_json)
        except Exception:
            return []

    @property
    def public_metadata(self) -> dict[str, Any]:
        try:
            return json.loads(self.public_metadata_snapshot_json)
        except Exception:
            return {}


class AppDefinition(Base):
    """Application project namespace in the App Zoo."""

    __tablename__ = "app_definitions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "app_key", name="uq_app_definition_workspace_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="DOCUMENT_ASSISTANT", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    owner_id: Mapped[str] = mapped_column(
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

    versions: Mapped[list[AppVersion]] = relationship(
        "AppVersion", back_populates="app_definition", cascade="all, delete-orphan", order_by="desc(AppVersion.created_at)"
    )


class AppVersion(Base):
    """Immutable version of an AI application configuration and package."""

    __tablename__ = "app_versions"
    __table_args__ = (
        UniqueConstraint("app_definition_id", "version_tag", name="uq_app_version_def_tag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    app_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Declarative canonical app manifest & digest
    app_manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Declared capabilities and I/O specifications
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_input_types_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_output_types_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    supported_languages_json: Mapped[str] = mapped_column(Text, default="[\"en\"]", nullable=False)
    license_id: Mapped[str] = mapped_column(String(64), default="Apache-2.0", nullable=False)

    # Resource requirements
    min_ram_mb: Mapped[float] = mapped_column(Float, default=4096.0, nullable=False)
    min_vram_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_hardware_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, BLOCKED, DEPRECATED
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    app_definition: Mapped[AppDefinition] = relationship("AppDefinition", back_populates="versions")
    model_dependencies: Mapped[list[AppModelDependency]] = relationship(
        "AppModelDependency", back_populates="app_version", cascade="all, delete-orphan"
    )

    @property
    def capabilities(self) -> list[str]:
        try:
            return json.loads(self.capabilities_json)
        except Exception:
            return []

    @property
    def supported_input_types(self) -> list[str]:
        try:
            return json.loads(self.supported_input_types_json)
        except Exception:
            return []

    @property
    def supported_output_types(self) -> list[str]:
        try:
            return json.loads(self.supported_output_types_json)
        except Exception:
            return []

    @property
    def supported_languages(self) -> list[str]:
        try:
            return json.loads(self.supported_languages_json)
        except Exception:
            return ["en"]

    @property
    def manifest(self) -> dict[str, Any]:
        try:
            return json.loads(self.app_manifest_json)
        except Exception:
            return {}


class AppModelDependency(Base):
    """Strict binding between an AppVersion and an approved M11 Model Version."""

    __tablename__ = "app_model_dependencies"
    __table_args__ = (
        UniqueConstraint("app_version_id", "model_version_id", name="uq_app_model_dep"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    app_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    release_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_role: Mapped[str] = mapped_column(String(64), default="PRIMARY_GENERATOR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )

    app_version: Mapped[AppVersion] = relationship("AppVersion", back_populates="model_dependencies")
    model_version: Mapped[Any] = relationship("ModelVersion", foreign_keys=[model_version_id])


class AppListing(Base):
    """Enterprise catalog entry for an App Version in the App Zoo."""

    __tablename__ = "app_listings"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_app_listing_workspace_slug"),
        UniqueConstraint("app_version_id", name="uq_app_listing_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="DOCUMENT_ASSISTANT", nullable=False, index=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    visibility: Mapped[CatalogVisibility] = mapped_column(
        Enum(CatalogVisibility, native_enum=False), default=CatalogVisibility.WORKSPACE, nullable=False, index=True
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.DRAFT, nullable=False, index=True
    )
    distribution_status: Mapped[DistributionStatus] = mapped_column(
        Enum(DistributionStatus, native_enum=False), default=DistributionStatus.METADATA_ONLY, nullable=False
    )

    public_metadata_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    publication_digest: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    app_version: Mapped[AppVersion] = relationship("AppVersion", foreign_keys=[app_version_id])
    app_definition: Mapped[AppDefinition] = relationship("AppDefinition", foreign_keys=[app_definition_id])
    hardware_snapshots: Mapped[list[HardwareCompatibilitySnapshot]] = relationship(
        "HardwareCompatibilitySnapshot",
        primaryjoin="and_(HardwareCompatibilitySnapshot.listing_id==AppListing.id, HardwareCompatibilitySnapshot.listing_type=='APP')",
        foreign_keys="HardwareCompatibilitySnapshot.listing_id",
        cascade="all, delete-orphan",
        overlaps="hardware_snapshots",
    )

    @property
    def tags(self) -> list[str]:
        try:
            return json.loads(self.tags_json)
        except Exception:
            return []

    @property
    def public_metadata(self) -> dict[str, Any]:
        try:
            return json.loads(self.public_metadata_snapshot_json)
        except Exception:
            return {}


class CatalogReview(Base):
    """Formal human review event for listing publications."""

    __tablename__ = "catalog_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    listing_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # MODEL or APP
    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVED, REJECTED, SUSPENDED
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    policy_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


class CatalogEvent(Base):
    """Append-only audit trail for catalog listing lifecycle transitions."""

    __tablename__ = "catalog_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    listing_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # MODEL or APP
    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    triggered_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )


class HardwareCompatibilitySnapshot(Base):
    """Hardware evidence badge linking catalog listings to verified or estimated performance."""

    __tablename__ = "hardware_compatibility_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    listing_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # MODEL or APP
    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    hardware_profile_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)

    compatibility_badge: Mapped[HardwareCompatibilityBadge] = mapped_column(
        Enum(HardwareCompatibilityBadge, native_enum=False), default=HardwareCompatibilityBadge.UNKNOWN, nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32), default="ESTIMATED", nullable=False)
    measured_or_estimated_values_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    limitations_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, server_default=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def metrics(self) -> dict[str, Any]:
        try:
            return json.loads(self.measured_or_estimated_values_json)
        except Exception:
            return {}
