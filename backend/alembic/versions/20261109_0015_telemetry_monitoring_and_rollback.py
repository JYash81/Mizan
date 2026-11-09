"""Add Production Telemetry, Monitoring, Metrics, SLOs, Alerting, Incident Management & Automated Rollback.

Revision ID: 20261109_0015
Revises: 20261109_0014
"""

import sqlalchemy as sa

from alembic import op

revision = "20261109_0015"
down_revision = "20261109_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. telemetry_configurations
    op.create_table(
        "telemetry_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("sync_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "consent_granted_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("consent_granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("metrics_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("events_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. metric_definitions
    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("metric_key", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metric_type", sa.String(32), nullable=False, server_default="GAUGE"),
        sa.Column("unit", sa.String(32), nullable=False, server_default=""),
        sa.Column("allowed_labels_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. metric_aggregates
    op.create_table(
        "metric_aggregates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("metric_key", sa.String(100), nullable=False, index=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_type", sa.String(16), nullable=False, server_default="HOURLY"),
        sa.Column("labels_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("min_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p95_value", sa.Float(), nullable=True),
        sa.Column("p99_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 4. operational_events
    op.create_table(
        "operational_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="INFO", index=True),
        sa.Column("source_component", sa.String(64), nullable=False, server_default="runtime"),
        sa.Column("summary", sa.String(255), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
    )

    # 5. alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metric_key", sa.String(100), nullable=False, index=True),
        sa.Column("condition_operator", sa.String(8), nullable=False, server_default="GT"),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("consecutive_breaches", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="WARNING"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("target_slot", sa.String(16), nullable=False, server_default="ANY"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 6. alert_instances
    op.create_table(
        "alert_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "rule_id",
            sa.String(36),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="NORMAL", index=True),
        sa.Column("current_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("breach_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_breached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_breached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("labels_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("annotations_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 7. alert_events
    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "alert_instance_id",
            sa.String(36),
            sa.ForeignKey("alert_instances.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("transition_reason", sa.Text(), nullable=True),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 8. alert_silences
    op.create_table(
        "alert_silences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "rule_id",
            sa.String(36),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 9. notification_policies
    op.create_table(
        "notification_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel_type", sa.String(32), nullable=False, server_default="LOCAL_STORE"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("min_severity", sa.String(16), nullable=False, server_default="WARNING"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 10. notification_deliveries
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "policy_id",
            sa.String(36),
            sa.ForeignKey("notification_policies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "alert_instance_id",
            sa.String(36),
            sa.ForeignKey("alert_instances.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="DELIVERED"),
        sa.Column("payload_summary", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 11. service_level_objectives
    op.create_table(
        "service_level_objectives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_percentage", sa.Float(), nullable=False, server_default="99.5"),
        sa.Column("rolling_window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("metric_key", sa.String(100), nullable=False, server_default="runtime_request_duration_ms"),
        sa.Column("good_events_definition", sa.Text(), nullable=False, server_default="latency_ms <= 2000"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 12. sli_snapshots
    op.create_table(
        "sli_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "slo_id",
            sa.String(36),
            sa.ForeignKey("service_level_objectives.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("good_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_sli_percentage", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("error_budget_remaining_percentage", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("has_sufficient_data", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 13. rollback_policies
    op.create_table(
        "rollback_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "runtime_application_id",
            sa.String(36),
            sa.ForeignKey("runtime_applications.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("mode", sa.String(32), nullable=False, server_default="MANUAL_ONLY"),
        sa.Column("evaluation_window_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("error_rate_threshold_percentage", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("latency_p95_threshold_ms", sa.Float(), nullable=False, server_default="2000.0"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("max_automatic_attempts_per_release", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("require_golden_test_pass", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_gate3_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 14. rollback_execution_events
    op.create_table(
        "rollback_execution_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "runtime_application_id",
            sa.String(36),
            sa.ForeignKey("runtime_applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_slot_name", sa.String(16), nullable=False),
        sa.Column("to_slot_name", sa.String(16), nullable=False),
        sa.Column("from_model_version_id", sa.String(36), nullable=True),
        sa.Column("to_model_version_id", sa.String(36), nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False, server_default="MANUAL"),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("golden_test_run_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUCCESS"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "executed_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 15. incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "customer_site_id",
            sa.String(36),
            sa.ForeignKey("customer_sites.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "runtime_application_id",
            sa.String(36),
            sa.ForeignKey("runtime_applications.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("incident_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="SEV2"),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN", index=True),
        sa.Column(
            "primary_alert_id",
            sa.String(36),
            sa.ForeignKey("alert_instances.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 16. incident_events
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.drop_table("rollback_execution_events")
    op.drop_table("rollback_policies")
    op.drop_table("sli_snapshots")
    op.drop_table("service_level_objectives")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_policies")
    op.drop_table("alert_silences")
    op.drop_table("alert_events")
    op.drop_table("alert_instances")
    op.drop_table("alert_rules")
    op.drop_table("operational_events")
    op.drop_table("metric_aggregates")
    op.drop_table("metric_definitions")
    op.drop_table("telemetry_configurations")
