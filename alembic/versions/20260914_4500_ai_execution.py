"""SIGMA AI execution engine

Revision ID: 20260914_4500
Revises: 20260914_4400
"""
from alembic import op
import sqlalchemy as sa

revision = "20260914_4500"
down_revision = "20260914_4400"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ai_action_proposals", sa.Column("execution_key", sa.String(length=64), nullable=True))
    op.create_index("ix_ai_action_proposals_execution_key", "ai_action_proposals", ["execution_key"], unique=True)


def downgrade():
    op.drop_index("ix_ai_action_proposals_execution_key", table_name="ai_action_proposals")
    op.drop_column("ai_action_proposals", "execution_key")
