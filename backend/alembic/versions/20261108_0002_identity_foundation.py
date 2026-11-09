"""identity security foundation

Revision ID: 20261108_0002
Revises: 20261108_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0002"
down_revision = "20261108_0001"
branch_labels = None
depends_on = None

account_status = sa.Enum(
    "PENDING_VERIFICATION",
    "ACTIVE",
    "SUSPENDED",
    "DEACTIVATED",
    name="account_status",
    native_enum=False,
    create_constraint=True,
)
token_purpose = sa.Enum(
    "EMAIL_VERIFICATION",
    "PASSWORD_RESET",
    name="token_purpose",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("normalized_email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("status", account_status, nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("normalized_email"),
    )
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"])
    for name, hash_column, extra in [
        (
            "auth_sessions",
            "session_token_hash",
            [
                sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("revoked_at", sa.DateTime(timezone=True)),
                sa.Column("revocation_reason", sa.String(255)),
            ],
        ),
        (
            "auth_tokens",
            "token_hash",
            [
                sa.Column("purpose", token_purpose, nullable=False),
                sa.Column("consumed_at", sa.DateTime(timezone=True)),
                sa.Column("revoked_at", sa.DateTime(timezone=True)),
            ],
        ),
    ]:
        op.create_table(
            name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(hash_column, sa.String(64), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            *extra,
            sa.UniqueConstraint(hash_column),
        )
        op.create_index(f"ix_{name}_user_id", name, ["user_id"])
        op.create_index(f"ix_{name}_{hash_column}", name, [hash_column])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("safe_metadata", sa.JSON()),
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])


def downgrade() -> None:
    for name in ("audit_events", "auth_tokens", "auth_sessions"):
        op.drop_table(name)
    op.drop_table("users")
