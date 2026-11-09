"""Add Model Zoo, App Zoo, Enterprise Catalog, and Hardware Compatibility snapshots.

Revision ID: 20261109_0013
Revises: 20261109_0012
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0013"
down_revision = "20261109_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. model_listings
    op.create_table(
        "model_listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_family_id",
            sa.String(36),
            sa.ForeignKey("model_families.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detailed_description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="GENERAL_CHAT", index=True),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("visibility", sa.String(32), nullable=False, server_default="WORKSPACE", index=True),
        sa.Column("publication_status", sa.String(32), nullable=False, server_default="DRAFT", index=True),
        sa.Column("distribution_status", sa.String(32), nullable=False, server_default="METADATA_ONLY"),
        sa.Column("public_metadata_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("publication_digest", sa.String(64), nullable=True, index=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "published_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_model_listing_workspace_slug"),
        sa.UniqueConstraint("model_version_id", name="uq_model_listing_version"),
    )

    # 2. app_definitions
    op.create_table(
        "app_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("app_key", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="DOCUMENT_ASSISTANT", index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "app_key", name="uq_app_definition_workspace_key"),
    )

    # 3. app_versions
    op.create_table(
        "app_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "app_definition_id",
            sa.String(36),
            sa.ForeignKey("app_definitions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_tag", sa.String(64), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("app_manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("manifest_digest", sa.String(64), nullable=False, index=True),
        sa.Column("capabilities_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_input_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_output_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_languages_json", sa.Text(), nullable=False, server_default='["en"]'),
        sa.Column("license_id", sa.String(64), nullable=False, server_default="Apache-2.0"),
        sa.Column("min_ram_mb", sa.Float(), nullable=False, server_default="4096.0"),
        sa.Column("min_vram_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("target_hardware_key", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_definition_id", "version_tag", name="uq_app_version_def_tag"),
    )

    # 4. app_model_dependencies
    op.create_table(
        "app_model_dependencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "app_version_id",
            sa.String(36),
            sa.ForeignKey("app_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_family_id",
            sa.String(36),
            sa.ForeignKey("model_families.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("release_manifest_digest", sa.String(64), nullable=False),
        sa.Column("dependency_role", sa.String(64), nullable=False, server_default="PRIMARY_GENERATOR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_version_id", "model_version_id", name="uq_app_model_dep"),
    )

    # 5. app_listings
    op.create_table(
        "app_listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "app_definition_id",
            sa.String(36),
            sa.ForeignKey("app_definitions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "app_version_id",
            sa.String(36),
            sa.ForeignKey("app_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detailed_description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False, server_default="DOCUMENT_ASSISTANT", index=True),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("visibility", sa.String(32), nullable=False, server_default="WORKSPACE", index=True),
        sa.Column("publication_status", sa.String(32), nullable=False, server_default="DRAFT", index=True),
        sa.Column("distribution_status", sa.String(32), nullable=False, server_default="METADATA_ONLY"),
        sa.Column("public_metadata_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("publication_digest", sa.String(64), nullable=True, index=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "published_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_app_listing_workspace_slug"),
        sa.UniqueConstraint("app_version_id", name="uq_app_listing_version"),
    )

    # 6. catalog_reviews
    op.create_table(
        "catalog_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_type", sa.String(32), nullable=False, index=True),
        sa.Column("listing_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "reviewer_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("policy_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 7. catalog_events
    op.create_table(
        "catalog_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_type", sa.String(32), nullable=False, index=True),
        sa.Column("listing_id", sa.String(36), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column(
            "triggered_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 8. hardware_compatibility_snapshots
    op.create_table(
        "hardware_compatibility_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_type", sa.String(32), nullable=False, index=True),
        sa.Column("listing_id", sa.String(36), nullable=False, index=True),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("hardware_profile_key", sa.String(64), nullable=False, index=True),
        sa.Column("artifact_digest", sa.String(64), nullable=True),
        sa.Column("compatibility_badge", sa.String(32), nullable=False, server_default="UNKNOWN", index=True),
        sa.Column("evidence_type", sa.String(32), nullable=False, server_default="ESTIMATED"),
        sa.Column("measured_or_estimated_values_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("limitations_notes", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("hardware_compatibility_snapshots")
    op.drop_table("catalog_events")
    op.drop_table("catalog_reviews")
    op.drop_table("app_listings")
    op.drop_table("app_model_dependencies")
    op.drop_table("app_versions")
    op.drop_table("app_definitions")
    op.drop_table("model_listings")
