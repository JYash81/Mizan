"""Add Sentinel v2 Security Architecture & Cryptographic Governance Tables.

Revision ID: 20261112_0016
Revises: 20261109_0015
"""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0016"
down_revision = "20261109_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. sentinel_containment_orders
    op.create_table(
        "sentinel_containment_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=False, index=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nonce", sa.String(64), index=True, nullable=False),
        sa.Column("is_cross_tenant", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dual_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "approver_1_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approver_2_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False, server_default=""),
        sa.Column("signature_purpose", sa.String(64), nullable=False, server_default="SENTINEL_CONTAINMENT_ORDER"),
        sa.Column("signer_key_id", sa.String(64), nullable=False, server_default="sentinel_decide_key"),
        sa.Column("execution_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_by_enforcer", sa.String(128), nullable=True),
        sa.Column("execution_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. sentinel_executed_nonces
    op.create_table(
        "sentinel_executed_nonces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nonce", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("order_id", sa.String(64), index=True, nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False, index=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. support_access_requests
    op.create_table(
        "support_access_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ticket_id", sa.String(64), index=True, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "requested_by_staff_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requested_scope", sa.String(32), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column(
            "approved_by_customer_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "second_approver_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("second_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_id", sa.String(64), nullable=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_break_glass", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("break_glass_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 4. support_session_logs
    op.create_table(
        "support_session_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "access_request_id",
            sa.String(36),
            sa.ForeignKey("support_access_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("workspace_id", sa.String(36), nullable=False, index=True),
        sa.Column("staff_user_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column("request_method", sa.String(16), nullable=False, server_default="GET"),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 5. sealed_evidence_records
    op.create_table(
        "sealed_evidence_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
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
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False, server_default="application/json"),
        sa.Column("encryption_key_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="SEALED"),
        sa.Column(
            "release_approver_1_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "release_approver_2_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 6. signed_version_floors
    op.create_table(
        "signed_version_floors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("minimum_version", sa.String(32), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False, server_default=""),
        sa.Column("signer_public_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 7. incident_regulatory_clocks
    op.create_table(
        "incident_regulatory_clocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("awareness_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gdpr_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_contract_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gdpr_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 8. sev1_recovery_records
    op.create_table(
        "sev1_recovery_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=False),
        sa.Column("triggering_actor_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "approver_1_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approver_1_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approver_2_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approver_2_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integrity_check_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("integrity_details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sev1_recovery_records")
    op.drop_table("incident_regulatory_clocks")
    op.drop_table("signed_version_floors")
    op.drop_table("sealed_evidence_records")
    op.drop_table("support_session_logs")
    op.drop_table("support_access_requests")
    op.drop_table("sentinel_executed_nonces")
    op.drop_table("sentinel_containment_orders")
