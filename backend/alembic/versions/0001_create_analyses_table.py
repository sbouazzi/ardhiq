"""create analyses table

Revision ID: 0001
Revises: 
Create Date: 2026-02-13

"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("offer_text", sa.Text(), nullable=False),
        sa.Column("user_context", sa.Text(), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("report_ar_md", sa.Text(), nullable=True),
        sa.Column("report_fr_md", sa.Text(), nullable=True),
        sa.Column("score_total", sa.Integer(), nullable=True),
        sa.Column("score_info", sa.Integer(), nullable=True),
        sa.Column("score_price", sa.Integer(), nullable=True),
        sa.Column("score_viability", sa.Integer(), nullable=True),
        sa.Column("score_risk", sa.Integer(), nullable=True),
        sa.Column("location_text", sa.Text(), nullable=True),
        sa.Column("area_ha", sa.Numeric(12, 3), nullable=True),
        sa.Column("price_tnd", sa.Numeric(14, 3), nullable=True),
        sa.Column("price_per_m2_tnd", sa.Numeric(14, 6), nullable=True),
        sa.Column("water_source", sa.String(length=64), nullable=True),
        sa.Column("water_depth_m", sa.Numeric(10, 3), nullable=True),
        sa.Column("tree_type", sa.String(length=64), nullable=True),
        sa.Column("tree_count", sa.Integer(), nullable=True),
        sa.Column("short_summary", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=True),
    )
#   op.create_index("ix_analyses_created_at", "analyses", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_analyses_created_at", table_name="analyses")
    op.drop_table("analyses")
