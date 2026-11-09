"""Add model families, model versions, registered artifacts, gate3 approvals, gate3 revocations, and release events.

Revision ID: 20261109_0012
Revises: 20261109_0011
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0012"
down_revision = "20261109_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. model_families
    op.create_table(
        "model_families",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=False, server_default="TEXT_GENERATION"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_model_family_workspace_slug"),
    )

    # 2. model_versions
    op.create_table(
        "model_versions",
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
            "family_id",
            sa.String(36),
            sa.ForeignKey("model_families.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_tag", sa.String(64), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT", index=True),
        sa.Column(
            "build_run_id",
            sa.String(36),
            sa.ForeignKey("model_build_runs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("source_model_key", sa.String(255), nullable=False),
        sa.Column("source_model_revision", sa.String(128), nullable=False),
        sa.Column("recipe_key", sa.String(64), nullable=False),
        sa.Column(
            "dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dataset_version_digest", sa.String(64), nullable=True),
        sa.Column(
            "gate1_approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("base_evaluation_score", sa.Float(), nullable=True),
        sa.Column("final_evaluation_score", sa.Float(), nullable=True),
        sa.Column("quality_delta", sa.Float(), nullable=True),
        sa.Column(
            "evaluation_run_id",
            sa.String(36),
            sa.ForeignKey("evaluation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("min_ram_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("min_vram_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("target_hardware_key", sa.String(64), nullable=True),
        sa.Column("release_manifest_json", sa.Text(), nullable=True),
        sa.Column("release_manifest_digest", sa.String(64), nullable=True, index=True),
        sa.Column("provenance_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("family_id", "version_tag", name="uq_model_version_family_tag"),
    )

    # 3. registered_artifacts
    op.create_table(
        "registered_artifacts",
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
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "staged_artifact_id",
            sa.String(36),
            sa.ForeignKey("staged_model_artifacts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("artifact_type", sa.String(64), nullable=False, index=True),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("quantization_type", sa.String(32), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("storage_reference", sa.String(512), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verification_details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_primary_weights", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("model_version_id", "sha256", name="uq_reg_artifact_version_sha"),
    )

    # 4. gate3_approvals
    op.create_table(
        "gate3_approvals",
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
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("release_manifest_digest", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False, index=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reviewer_role_snapshot", sa.String(32), nullable=False),
        sa.Column("signature_algorithm", sa.String(32), nullable=False, server_default="Ed25519"),
        sa.Column("signature_purpose", sa.String(64), nullable=False, server_default="GATE3_RELEASE_APPROVAL"),
        sa.Column("signing_key_id", sa.String(64), nullable=False),
        sa.Column("approval_signature", sa.String(256), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 5. gate3_revocations
    op.create_table(
        "gate3_revocations",
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
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "gate3_approval_id",
            sa.String(36),
            sa.ForeignKey("gate3_approvals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "revoked_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revoked_by_role_snapshot", sa.String(32), nullable=False),
        sa.Column("revocation_reason", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 6. model_release_events
    op.create_table(
        "model_release_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
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


def downgrade() -> None:
    op.drop_table("model_release_events")
    op.drop_table("gate3_revocations")
    op.drop_table("gate3_approvals")
    op.drop_table("registered_artifacts")
    op.drop_table("model_versions")
    op.drop_table("model_families")
