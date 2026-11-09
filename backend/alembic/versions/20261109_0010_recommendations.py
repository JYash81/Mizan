"""Add recommendation engine, optimization profiles, candidates, scenarios, decisions, and audit events.

Revision ID: 20261109_0010
Revises: 20261108_0009
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0010"
down_revision = "20261108_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. recommendation_runs
    op.create_table(
        "recommendation_runs",
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
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="DRAFT"),
        sa.Column("algorithm_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("input_digest", sa.String(64), nullable=False, index=True),
        sa.Column("result_digest", sa.String(64), nullable=True, index=True),
        sa.Column("input_snapshot_json", sa.Text(), nullable=False),
        sa.Column("normalization_snapshot_json", sa.Text(), nullable=True),
        sa.Column("weights_snapshot_json", sa.Text(), nullable=True),
        sa.Column("constraints_snapshot_json", sa.Text(), nullable=True),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("frontier_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # 2. recommendation_candidates
    op.create_table(
        "recommendation_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            sa.String(36),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "experiment_id",
            sa.String(36),
            sa.ForeignKey("experiments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "experiment_trial_id",
            sa.String(36),
            sa.ForeignKey("experiment_trials.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("candidate_label", sa.String(255), nullable=False),
        sa.Column("configuration_digest", sa.String(128), nullable=False, index=True),
        sa.Column("configuration_json", sa.Text(), nullable=False),
        sa.Column("evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("dataset_id", sa.String(36), nullable=True),
        sa.Column("dataset_version_id", sa.String(36), nullable=True),
        sa.Column("evaluation_suite_id", sa.String(36), nullable=True),
        sa.Column("evaluation_suite_version_id", sa.String(36), nullable=True),
        sa.Column("evaluation_split", sa.String(32), nullable=True),
        sa.Column("hardware_profile_key", sa.String(64), nullable=True),
        sa.Column("provenance_status", sa.String(32), nullable=False, server_default="VERIFIED"),
        sa.Column("eligibility_status", sa.String(32), nullable=False, server_default="ELIGIBLE"),
        sa.Column("exclusion_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("objective_values_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("normalized_objective_values_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("constraint_results_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("pareto_frontier_member", sa.Boolean(), nullable=False, server_default="0", index=True),
        sa.Column("dominated_by_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("dominates_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("weighted_score", sa.Float(), nullable=True),
        sa.Column("evidence_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("explanation_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 3. optimization_profiles
    op.create_table(
        "optimization_profiles",
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
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objectives_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("weights_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("constraints_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("preferred_hardware_profile", sa.String(64), nullable=True),
        sa.Column("budget_currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "name", name="uq_workspace_optimization_profile_name"),
    )

    # 4. recommendation_scenarios
    op.create_table(
        "recommendation_scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            sa.String(36),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scenario_name", sa.String(128), nullable=False),
        sa.Column("weight_snapshot_json", sa.Text(), nullable=False),
        sa.Column("ranking_snapshot_json", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 5. recommendation_decisions
    op.create_table(
        "recommendation_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            sa.String(36),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "selected_candidate_id",
            sa.String(36),
            sa.ForeignKey("recommendation_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision", sa.String(64), nullable=False, index=True),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 6. recommendation_events
    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            sa.String(36),
            sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("recommendation_events")
    op.drop_table("recommendation_decisions")
    op.drop_table("recommendation_scenarios")
    op.drop_table("optimization_profiles")
    op.drop_table("recommendation_candidates")
    op.drop_table("recommendation_runs")
