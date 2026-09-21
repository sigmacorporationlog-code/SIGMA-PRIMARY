"""sync v2.2 delivery acknowledgements

Revision ID: 20260913_2200
Revises: 20260913_2100
"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_2200"
down_revision = "20260913_2100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sync_delivery_acks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("operation_id", sa.String(length=100), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "device_id", "operation_id", name="uq_sync_delivery_ack"),
    )
    op.create_index("ix_sync_delivery_acks_school_id", "sync_delivery_acks", ["school_id"])
    op.create_index("ix_sync_delivery_acks_device_id", "sync_delivery_acks", ["device_id"])
    op.create_index("ix_sync_delivery_acks_operation_id", "sync_delivery_acks", ["operation_id"])


def downgrade():
    op.drop_index("ix_sync_delivery_acks_operation_id", table_name="sync_delivery_acks")
    op.drop_index("ix_sync_delivery_acks_device_id", table_name="sync_delivery_acks")
    op.drop_index("ix_sync_delivery_acks_school_id", table_name="sync_delivery_acks")
    op.drop_table("sync_delivery_acks")
