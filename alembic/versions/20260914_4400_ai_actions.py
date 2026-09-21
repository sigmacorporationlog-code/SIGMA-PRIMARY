"""SIGMA AI Action Center

Revision ID: 20260914_4400
Revises: 20260914_4300
"""
from alembic import op
import sqlalchemy as sa

revision = "20260914_4400"
down_revision = "20260914_4300"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_action_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("ai_interaction_id", sa.Integer(), sa.ForeignKey("ai_interactions.id"), nullable=True),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_ai_action_proposals_school_id", "ai_action_proposals", ["school_id"])
    op.create_index("ix_ai_action_proposals_created_by_user_id", "ai_action_proposals", ["created_by_user_id"])
    op.create_index("ix_ai_action_proposals_approved_by_user_id", "ai_action_proposals", ["approved_by_user_id"])
    op.create_index("ix_ai_action_proposals_ai_interaction_id", "ai_action_proposals", ["ai_interaction_id"])
    op.create_index("ix_ai_action_proposals_action_type", "ai_action_proposals", ["action_type"])
    op.create_index("ix_ai_action_proposals_status", "ai_action_proposals", ["status"])


def downgrade():
    for idx in [
        "ix_ai_action_proposals_status", "ix_ai_action_proposals_action_type",
        "ix_ai_action_proposals_ai_interaction_id", "ix_ai_action_proposals_approved_by_user_id",
        "ix_ai_action_proposals_created_by_user_id", "ix_ai_action_proposals_school_id",
    ]:
        op.drop_index(idx, table_name="ai_action_proposals")
    op.drop_table("ai_action_proposals")
