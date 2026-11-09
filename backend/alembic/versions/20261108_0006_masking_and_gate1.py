"""add masking_profiles, masking_runs, pii_findings, masking_decisions, gate1_approvals, and gate1_approval_events

Revision ID: 20261108_0006
Revises: 20261108_0005
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0006"
down_revision = "20261108_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. masking_profiles
    op.create_table(
        "masking_profiles",
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
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("enabled_entities_json", sa.Text(), nullable=False),
        sa.Column(
            "replacement_strategy",
            sa.String(32),
            nullable=False,
            server_default="REPLACE_WITH_ENTITY_LABEL",
        ),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_masking_profiles_org_id", "masking_profiles", ["organization_id"])
    op.create_index("ix_masking_profiles_ws_id", "masking_profiles", ["workspace_id"])

    # 2. masking_runs
    op.create_table(
        "masking_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column("source_dataset_digest", sa.String(64), nullable=False),
        sa.Column(
            "masking_profile_id",
            sa.String(36),
            sa.ForeignKey("masking_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column(
            "extraction_coverage",
            sa.String(32),
            nullable=False,
            server_default="EXTRACTION_COMPLETE",
        ),
        sa.Column("documents_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unresolved_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("masked_output_digest", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_masking_runs_ws_id", "masking_runs", ["workspace_id"])
    op.create_index("ix_masking_runs_dataset_id", "masking_runs", ["dataset_id"])
    op.create_index("ix_masking_runs_ver_id", "masking_runs", ["dataset_version_id"])
    op.create_index("ix_masking_runs_status", "masking_runs", ["status"])

    # 3. pii_findings
    op.create_table(
        "pii_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "masking_run_id",
            sa.String(36),
            sa.ForeignKey("masking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("recognizer_name", sa.String(120), nullable=False),
        sa.Column("recognizer_version", sa.String(32), nullable=False, server_default="1.0"),
        sa.Column("detection_score", sa.Float(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("offset_unit", sa.String(32), nullable=False, server_default="unicode_codepoint"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("overlap_group_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DETECTED"),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pii_findings_run_id", "pii_findings", ["masking_run_id"])
    op.create_index("ix_pii_findings_doc_id", "pii_findings", ["document_id"])
    op.create_index("ix_pii_findings_entity_type", "pii_findings", ["entity_type"])
    op.create_index("ix_pii_findings_status", "pii_findings", ["status"])
    op.create_index("ix_pii_findings_overlap_group", "pii_findings", ["overlap_group_id"])

    # 4. masking_decisions
    op.create_table(
        "masking_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "masking_run_id",
            sa.String(36),
            sa.ForeignKey("masking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("pii_findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision_type", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("custom_replacement", sa.String(120), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_masking_decisions_run_id", "masking_decisions", ["masking_run_id"])
    op.create_index("ix_masking_decisions_finding_id", "masking_decisions", ["finding_id"])

    # 5. gate1_approvals
    op.create_table(
        "gate1_approvals",
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
            "masking_run_id",
            sa.String(36),
            sa.ForeignKey("masking_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_dataset_digest", sa.String(64), nullable=False),
        sa.Column("masked_output_digest", sa.String(64), nullable=False),
        sa.Column("findings_digest", sa.String(64), nullable=False),
        sa.Column("reviewer_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_role_snapshot", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False, server_default="APPROVED"),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("signature_algorithm", sa.String(32), nullable=False, server_default="Ed25519"),
        sa.Column("signing_key_id", sa.String(64), nullable=False),
        sa.Column("approval_signature", sa.String(256), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_gate1_approvals_org_id", "gate1_approvals", ["organization_id"])
    op.create_index("ix_gate1_approvals_ws_id", "gate1_approvals", ["workspace_id"])
    op.create_index("ix_gate1_approvals_dataset_id", "gate1_approvals", ["dataset_id"])
    op.create_index("ix_gate1_approvals_ver_id", "gate1_approvals", ["dataset_version_id"])
    op.create_index("ix_gate1_approvals_run_id", "gate1_approvals", ["masking_run_id"])
    op.create_index("ix_gate1_approvals_decision", "gate1_approvals", ["decision"])

    # 6. gate1_approval_events
    op.create_table(
        "gate1_approval_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "approval_id",
            sa.String(36),
            sa.ForeignKey("gate1_approvals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_gate1_approval_events_approval_id", "gate1_approval_events", ["approval_id"]
    )
    op.create_index("ix_gate1_approval_events_event_type", "gate1_approval_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("gate1_approval_events")
    op.drop_table("gate1_approvals")
    op.drop_table("masking_decisions")
    op.drop_table("pii_findings")
    op.drop_table("masking_runs")
    op.drop_table("masking_profiles")
