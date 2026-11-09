"""add experiments, experiment_trials, and experiment_events

Revision ID: 20261108_0008
Revises: 20261108_0007
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0008"
down_revision = "20261108_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. experiments
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column(
            "dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gate1_approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dataset_digest", sa.String(128), nullable=True),
        sa.Column(
            "evaluation_suite_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_suite_version_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suite_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_suite_digest", sa.String(128), nullable=True),
        sa.Column("evaluation_split", sa.String(32), nullable=False, server_default="VALIDATION"),
        sa.Column("baseline_config_json", sa.Text(), nullable=True),
        sa.Column("configuration_digest", sa.String(128), nullable=True),
        sa.Column("total_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancelled_trials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_workspace_experiment_slug"),
    )
    op.create_index("ix_experiments_organization_id", "experiments", ["organization_id"])
    op.create_index("ix_experiments_workspace_id", "experiments", ["workspace_id"])
    op.create_index("ix_experiments_slug", "experiments", ["slug"])
    op.create_index("ix_experiments_status", "experiments", ["status"])

    # 2. experiment_trials
    op.create_table(
        "experiment_trials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "experiment_id",
            sa.String(36),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trial_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("configuration_json", sa.Text(), nullable=False),
        sa.Column("configuration_digest", sa.String(128), nullable=False),
        sa.Column(
            "evaluation_run_id",
            sa.String(36),
            sa.ForeignKey("evaluation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("aggregate_score", sa.Float(), nullable=True),
        sa.Column("score_breakdown_json", sa.Text(), nullable=True),
        sa.Column("latency_p50_ms", sa.Float(), nullable=True),
        sa.Column("latency_p95_ms", sa.Float(), nullable=True),
        sa.Column("latency_p99_ms", sa.Float(), nullable=True),
        sa.Column("execution_duration_ms", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("experiment_id", "trial_number", name="uq_experiment_trial_number"),
    )
    op.create_index("ix_experiment_trials_organization_id", "experiment_trials", ["organization_id"])
    op.create_index("ix_experiment_trials_workspace_id", "experiment_trials", ["workspace_id"])
    op.create_index("ix_experiment_trials_experiment_id", "experiment_trials", ["experiment_id"])
    op.create_index("ix_experiment_trials_status", "experiment_trials", ["status"])
    op.create_index("ix_experiment_trials_configuration_digest", "experiment_trials", ["configuration_digest"])

    # 3. experiment_events
    op.create_table(
        "experiment_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "experiment_id",
            sa.String(36),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trial_id",
            sa.String(36),
            sa.ForeignKey("experiment_trials.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("previous_status", sa.String(64), nullable=True),
        sa.Column("new_status", sa.String(64), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_experiment_events_experiment_id", "experiment_events", ["experiment_id"])
    op.create_index("ix_experiment_events_trial_id", "experiment_events", ["trial_id"])
    op.create_index("ix_experiment_events_event_type", "experiment_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_experiment_events_event_type", table_name="experiment_events")
    op.drop_index("ix_experiment_events_trial_id", table_name="experiment_events")
    op.drop_index("ix_experiment_events_experiment_id", table_name="experiment_events")
    op.drop_table("experiment_events")

    op.drop_index("ix_experiment_trials_configuration_digest", table_name="experiment_trials")
    op.drop_index("ix_experiment_trials_status", table_name="experiment_trials")
    op.drop_index("ix_experiment_trials_experiment_id", table_name="experiment_trials")
    op.drop_index("ix_experiment_trials_workspace_id", table_name="experiment_trials")
    op.drop_index("ix_experiment_trials_organization_id", table_name="experiment_trials")
    op.drop_table("experiment_trials")

    op.drop_index("ix_experiments_status", table_name="experiments")
    op.drop_index("ix_experiments_slug", table_name="experiments")
    op.drop_index("ix_experiments_workspace_id", table_name="experiments")
    op.drop_index("ix_experiments_organization_id", table_name="experiments")
    op.drop_table("experiments")
