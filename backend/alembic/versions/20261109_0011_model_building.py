"""Add model sources, recipes, external processing authorizations, build runs, checkpoints, events, staged artifacts, and evaluation links.

Revision ID: 20261109_0011
Revises: 20261109_0010
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0011"
down_revision = "20261109_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. model_sources
    op.create_table(
        "model_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_key", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_repository", sa.String(64), nullable=False, server_default="huggingface"),
        sa.Column("immutable_revision", sa.String(128), nullable=False, index=True),
        sa.Column("architecture", sa.String(128), nullable=False, index=True),
        sa.Column("parameter_count_millions", sa.Float(), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("tokenizer_digest", sa.String(64), nullable=True),
        sa.Column("config_digest", sa.String(64), nullable=True),
        sa.Column("license_id", sa.String(128), nullable=False),
        sa.Column("license_status", sa.String(32), nullable=False, server_default="UNKNOWN_LICENSE"),
        sa.Column("license_url", sa.String(512), nullable=True),
        sa.Column("commercial_use_allowed", sa.Boolean(), nullable=True),
        sa.Column("is_gated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("access_status", sa.String(32), nullable=False, server_default="PUBLIC"),
        sa.Column("requires_custom_code", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("estimated_download_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("source_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("model_key", "immutable_revision", name="uq_model_source_key_rev"),
    )

    # 2. model_build_recipes
    op.create_table(
        "model_build_recipes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipe_key", sa.String(128), nullable=False, index=True),
        sa.Column("recipe_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("recipe_type", sa.String(32), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("supported_architectures_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("supported_runtimes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("configuration_schema_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("default_config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("dependency_lock_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("resource_requirements_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_executable_locally", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("recipe_key", "recipe_version", name="uq_recipe_key_version"),
    )

    # 3. external_processing_authorizations
    op.create_table(
        "external_processing_authorizations",
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
            "dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("dataset_version_digest", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("destination_class", sa.String(64), nullable=False, server_default="GOOGLE_COLAB_EPHEMERAL_RUNTIME"),
        sa.Column(
            "authorized_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("authorization_token", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 4. model_build_runs
    op.create_table(
        "model_build_runs",
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
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="DRAFT"),
        sa.Column("execution_mode", sa.String(32), nullable=False, server_default="LOCAL_SMOKE_TEST"),
        sa.Column(
            "source_model_id",
            sa.String(36),
            sa.ForeignKey("model_sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_revision", sa.String(128), nullable=False),
        sa.Column(
            "recipe_id",
            sa.String(36),
            sa.ForeignKey("model_build_recipes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("recipe_key", sa.String(128), nullable=False),
        sa.Column(
            "recommendation_run_id",
            sa.String(36),
            sa.ForeignKey("recommendation_runs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "recommendation_candidate_id",
            sa.String(36),
            sa.ForeignKey("recommendation_candidates.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "gate1_approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "external_processing_authorization_id",
            sa.String(36),
            sa.ForeignKey("external_processing_authorizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("training_config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("build_manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("manifest_digest", sa.String(64), nullable=False, index=True),
        sa.Column("preflight_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("train_partition_digest", sa.String(64), nullable=True),
        sa.Column("val_partition_digest", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 5. model_build_checkpoints
    op.create_table(
        "model_build_checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "build_run_id",
            sa.String(36),
            sa.ForeignKey("model_build_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("checkpoint_number", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("storage_reference", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("configuration_digest", sa.String(64), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 6. model_build_events
    op.create_table(
        "model_build_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "build_run_id",
            sa.String(36),
            sa.ForeignKey("model_build_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 7. staged_model_artifacts
    op.create_table(
        "staged_model_artifacts",
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
            "build_run_id",
            sa.String(36),
            sa.ForeignKey("model_build_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("artifact_type", sa.String(32), nullable=False, index=True),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("storage_reference", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("source_model_key", sa.String(255), nullable=False),
        sa.Column("source_model_revision", sa.String(128), nullable=False),
        sa.Column("quantization_type", sa.String(32), nullable=True),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("model_config_digest", sa.String(64), nullable=True),
        sa.Column("tokenizer_reference", sa.String(255), nullable=True),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="PENDING_VERIFICATION"),
        sa.Column("verification_details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_staged_for_m11", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 8. model_evaluation_links
    op.create_table(
        "model_evaluation_links",
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
            "build_run_id",
            sa.String(36),
            sa.ForeignKey("model_build_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "staged_artifact_id",
            sa.String(36),
            sa.ForeignKey("staged_model_artifacts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evaluation_run_id",
            sa.String(36),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("model_role", sa.String(32), nullable=False, index=True),
        sa.Column("evaluation_suite_id", sa.String(36), nullable=False),
        sa.Column("evaluation_split", sa.String(32), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("quality_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_delta_ms", sa.Float(), nullable=True),
        sa.Column("memory_delta_mb", sa.Float(), nullable=True),
        sa.Column("comparison_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("model_evaluation_links")
    op.drop_table("staged_model_artifacts")
    op.drop_table("model_build_events")
    op.drop_table("model_build_checkpoints")
    op.drop_table("model_build_runs")
    op.drop_table("external_processing_authorizations")
    op.drop_table("model_build_recipes")
    op.drop_table("model_sources")
