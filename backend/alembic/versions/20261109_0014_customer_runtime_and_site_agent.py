"""Add Customer Runtime, Site Agent, Blue/Green Slots, and Golden Test Runner.

Revision ID: 20261109_0014
Revises: 20261109_0013
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0014"
down_revision = "20261109_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. customer_sites
    op.create_table(
        "customer_sites",
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
        sa.Column("site_key", sa.String(100), nullable=False),
        sa.Column("site_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ENROLLING", index=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "site_key", name="uq_site_workspace_key"),
    )

    # 2. site_enrollment_tokens
    op.create_table(
        "site_enrollment_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. site_agent_identities
    op.create_table(
        "site_agent_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("agent_id", sa.String(36), nullable=False, unique=True),
        sa.Column("public_key_fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("key_id", sa.String(100), nullable=False),
        sa.Column("protocol_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runtime_version", sa.String(64), nullable=True),
        sa.Column("agent_version", sa.String(64), nullable=True),
        sa.Column("platform_info_json", sa.Text(), nullable=False, server_default="{}"),
    )

    # 4. runtime_applications
    op.create_table(
        "runtime_applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "app_definition_id",
            sa.String(36),
            sa.ForeignKey("app_definitions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "app_version_id",
            sa.String(36),
            sa.ForeignKey("app_versions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("app_manifest_digest", sa.String(64), nullable=False),
        sa.Column("active_slot_name", sa.String(16), nullable=False, server_default="SLOT_A"),
        sa.Column("status", sa.String(32), nullable=False, server_default="INSTALLED"),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("customer_site_id", "app_definition_id", name="uq_site_app_def"),
    )

    # 5. runtime_slots
    op.create_table(
        "runtime_slots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "runtime_application_id",
            sa.String(36),
            sa.ForeignKey("runtime_applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slot_name", sa.String(16), nullable=False, server_default="SLOT_A"),
        sa.Column(
            "app_version_id",
            sa.String(36),
            sa.ForeignKey("app_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "model_version_id",
            sa.String(36),
            sa.ForeignKey("model_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("release_manifest_digest", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="EMPTY", index=True),
        sa.Column("readiness_state", sa.String(32), nullable=False, server_default="UNINITIALIZED"),
        sa.Column("golden_test_status", sa.String(32), nullable=False, server_default="NOT_RUN"),
        sa.Column("last_golden_test_run_id", sa.String(36), nullable=True),
        sa.Column("engine_adapter_key", sa.String(64), nullable=False, server_default="MOCK_ENGINE"),
        sa.Column("configuration_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("staged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("runtime_application_id", "slot_name", name="uq_app_slot_name"),
    )

    # 6. golden_test_suites
    op.create_table(
        "golden_test_suites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "app_version_id",
            sa.String(36),
            sa.ForeignKey("app_versions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("suite_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("suite_digest", sa.String(64), nullable=False, index=True),
        sa.Column("cases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_version_id", "suite_version", name="uq_app_suite_version"),
    )

    # 7. golden_test_runs
    op.create_table(
        "golden_test_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "runtime_slot_id",
            sa.String(36),
            sa.ForeignKey("runtime_slots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("golden_test_suites.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("suite_digest", sa.String(64), nullable=False),
        sa.Column("runtime_version", sa.String(64), nullable=False, server_default="1.0.0"),
        sa.Column("outcome", sa.String(32), nullable=False, server_default="NOT_RUN", index=True),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("results_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 8. site_agent_commands
    op.create_table(
        "site_agent_commands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("command_id", sa.String(36), nullable=False, unique=True),
        sa.Column("command_type", sa.String(64), nullable=False, index=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signature", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING", index=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 9. runtime_activation_events
    op.create_table(
        "runtime_activation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "runtime_application_id",
            sa.String(36),
            sa.ForeignKey("runtime_applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("previous_slot_name", sa.String(16), nullable=False),
        sa.Column("new_slot_name", sa.String(16), nullable=False),
        sa.Column("model_version_id", sa.String(36), nullable=False),
        sa.Column("app_version_id", sa.String(36), nullable=False),
        sa.Column("release_manifest_digest", sa.String(64), nullable=False),
        sa.Column("golden_test_run_id", sa.String(36), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("switch_reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("runtime_activation_events")
    op.drop_table("site_agent_commands")
    op.drop_table("golden_test_runs")
    op.drop_table("golden_test_suites")
    op.drop_table("runtime_slots")
    op.drop_table("runtime_applications")
    op.drop_table("site_agent_identities")
    op.drop_table("site_enrollment_tokens")
    op.drop_table("customer_sites")
