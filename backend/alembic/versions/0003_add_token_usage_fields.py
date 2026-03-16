"""add token usage + model_used fields to analyses

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-14

"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("model_used", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("output_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("total_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analyses", "total_tokens")
    op.drop_column("analyses", "output_tokens")
    op.drop_column("analyses", "input_tokens")
    op.drop_column("analyses", "model_used")
