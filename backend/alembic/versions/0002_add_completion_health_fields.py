"""add completion health fields to analyses

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-14

"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ok"),
    )
    op.add_column(
        "analyses",
        sa.Column("error_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analyses", "error_message")
    op.drop_column("analyses", "error_code")
    op.drop_column("analyses", "status")
