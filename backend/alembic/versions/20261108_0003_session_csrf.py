"""add session CSRF digest

Revision ID: 20261108_0003
Revises: 20261108_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108_0003"
down_revision = "20261108_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch:
        batch.add_column(sa.Column("csrf_token_hash", sa.String(64), nullable=True))
        batch.create_unique_constraint("uq_auth_sessions_csrf_token_hash", ["csrf_token_hash"])


def downgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch:
        batch.drop_constraint("uq_auth_sessions_csrf_token_hash", type_="unique")
        batch.drop_column("csrf_token_hash")
