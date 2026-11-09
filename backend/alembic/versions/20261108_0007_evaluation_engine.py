"""add evaluation_suites, evaluation_suite_versions, evaluation_cases, evaluation_rubrics, rubric_criteria, evaluation_runs, evaluation_case_results, evaluation_metric_results, and evaluation_reviews

Revision ID: 20261108_0007
Revises: 20261108_0006
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0007"
down_revision = "20261108_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. evaluation_suites
    op.create_table(
        "evaluation_suites",
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
        sa.Column("domain", sa.String(100), nullable=False, server_default="general"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column(
            "source_dataset_id",
            sa.String(36),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "gate1_approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generation_method", sa.String(64), nullable=False, server_default="rule_based"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_suites_organization_id", "evaluation_suites", ["organization_id"])
    op.create_index("ix_evaluation_suites_workspace_id", "evaluation_suites", ["workspace_id"])
    op.create_index("ix_evaluation_suites_slug", "evaluation_suites", ["slug"])

    # 2. evaluation_suite_versions
    op.create_table(
        "evaluation_suite_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("suite_digest", sa.String(64), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rubric_id", sa.String(36), nullable=True),
        sa.Column("rubric_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_dataset_version_id", sa.String(36), nullable=True),
        sa.Column("source_dataset_digest", sa.String(64), nullable=True),
        sa.Column("gate1_approval_id", sa.String(36), nullable=True),
        sa.Column("generation_config_digest", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="FINALIZED"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_suite_versions_suite_id", "evaluation_suite_versions", ["suite_id"])

    # 3. evaluation_cases
    op.create_table(
        "evaluation_cases",
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
            "suite_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suite_version_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suite_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("case_type", sa.String(64), nullable=False, server_default="standard"),
        sa.Column("category", sa.String(32), nullable=False, server_default="FACTUAL"),
        sa.Column("difficulty", sa.String(32), nullable=False, server_default="MEDIUM"),
        sa.Column("split", sa.String(32), nullable=False, server_default="DEVELOPMENT"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("is_unanswerable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_document_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_chunk_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_offsets_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("ground_truth_status", sa.String(32), nullable=False, server_default="GENERATED"),
        sa.Column("generation_method", sa.String(64), nullable=False, server_default="rule_based"),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_cases_organization_id", "evaluation_cases", ["organization_id"])
    op.create_index("ix_evaluation_cases_workspace_id", "evaluation_cases", ["workspace_id"])
    op.create_index("ix_evaluation_cases_suite_id", "evaluation_cases", ["suite_id"])
    op.create_index("ix_evaluation_cases_suite_version_id", "evaluation_cases", ["suite_version_id"])

    # 4. evaluation_rubrics
    op.create_table(
        "evaluation_rubrics",
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
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("domain", sa.String(100), nullable=False, server_default="general"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_rubrics_organization_id", "evaluation_rubrics", ["organization_id"])
    op.create_index("ix_evaluation_rubrics_workspace_id", "evaluation_rubrics", ["workspace_id"])

    # 5. rubric_criteria
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "rubric_id",
            sa.String(36),
            sa.ForeignKey("evaluation_rubrics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("criterion_key", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scoring_method", sa.String(32), nullable=False, server_default="EXACT_MATCH"),
        sa.Column("maximum_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("minimum_acceptable_score", sa.Float(), nullable=False, server_default="70.0"),
        sa.Column("configuration_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rubric_criteria_rubric_id", "rubric_criteria", ["rubric_id"])
    op.create_index("ix_rubric_criteria_criterion_key", "rubric_criteria", ["criterion_key"])

    # 6. evaluation_runs
    op.create_table(
        "evaluation_runs",
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
            "suite_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suite_version_id",
            sa.String(36),
            sa.ForeignKey("evaluation_suite_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rubric_id", sa.String(36), nullable=True),
        sa.Column("rubric_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("target_type", sa.String(32), nullable=False, server_default="RAG_PIPELINE"),
        sa.Column("target_name", sa.String(255), nullable=False, server_default="default-rag"),
        sa.Column("provider_name", sa.String(64), nullable=False, server_default="mock"),
        sa.Column("model_name", sa.String(128), nullable=False, server_default="mock-gpt-mizan-v1"),
        sa.Column("retrieval_config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("score_breakdown_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_runs_organization_id", "evaluation_runs", ["organization_id"])
    op.create_index("ix_evaluation_runs_workspace_id", "evaluation_runs", ["workspace_id"])
    op.create_index("ix_evaluation_runs_suite_id", "evaluation_runs", ["suite_id"])
    op.create_index("ix_evaluation_runs_suite_version_id", "evaluation_runs", ["suite_version_id"])

    # 7. evaluation_case_results
    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actual_answer", sa.Text(), nullable=True),
        sa.Column("actual_answer_digest", sa.String(64), nullable=True),
        sa.Column("overall_case_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="COMPLETED"),
        sa.Column("retrieved_chunks_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("citations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_case_results_run_id", "evaluation_case_results", ["run_id"])
    op.create_index("ix_evaluation_case_results_case_id", "evaluation_case_results", ["case_id"])

    # 8. evaluation_metric_results
    op.create_table(
        "evaluation_metric_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_result_id",
            sa.String(36),
            sa.ForeignKey("evaluation_case_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_key", sa.String(64), nullable=False),
        sa.Column("raw_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("normalized_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("score_scale", sa.String(32), nullable=False, server_default="0-100"),
        sa.Column("status", sa.String(32), nullable=False, server_default="MEASURED"),
        sa.Column("evaluator_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_metric_results_case_result_id", "evaluation_metric_results", ["case_result_id"])
    op.create_index("ix_evaluation_metric_results_metric_key", "evaluation_metric_results", ["metric_key"])

    # 9. evaluation_reviews
    op.create_table(
        "evaluation_reviews",
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
            "case_id",
            sa.String(36),
            sa.ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_evaluation_reviews_organization_id", "evaluation_reviews", ["organization_id"])
    op.create_index("ix_evaluation_reviews_workspace_id", "evaluation_reviews", ["workspace_id"])
    op.create_index("ix_evaluation_reviews_case_id", "evaluation_reviews", ["case_id"])


def downgrade() -> None:
    op.drop_table("evaluation_reviews")
    op.drop_table("evaluation_metric_results")
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
    op.drop_table("rubric_criteria")
    op.drop_table("evaluation_rubrics")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_suite_versions")
    op.drop_table("evaluation_suites")
