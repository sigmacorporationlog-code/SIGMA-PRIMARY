"""SIGMA Intelligence foundation

Revision ID: 20260914_4300
Revises: 20260914_4200
"""
from alembic import op
import sqlalchemy as sa

revision = "20260914_4300"
down_revision = "20260914_4200"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("intent", sa.String(length=80), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("contains_personal_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_ai_interactions_school_id", "ai_interactions", ["school_id"])
    op.create_index("ix_ai_interactions_user_id", "ai_interactions", ["user_id"])
    op.create_index("ix_ai_interactions_prompt_hash", "ai_interactions", ["prompt_hash"])


def downgrade():
    op.drop_index("ix_ai_interactions_prompt_hash", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_user_id", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_school_id", table_name="ai_interactions")
    op.drop_table("ai_interactions")
