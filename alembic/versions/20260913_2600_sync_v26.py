"""v2.6: traçabilité et résolution explicite des conflits de synchronisation.

Revision ID: 20260913_2600
Revises: 20260913_2500
"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_2600"
down_revision = "20260913_2500"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("sync_operations") as batch:
        batch.add_column(sa.Column("resolution", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("resolved_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("superseded_by_operation_id", sa.String(length=100), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("sync_operations") as batch:
        batch.drop_column("superseded_by_operation_id")
        batch.drop_column("resolved_by_id")
        batch.drop_column("resolved_at")
        batch.drop_column("resolution")
