"""SIGMA BADGE 3.5 lifecycle fields

Revision ID: 20260914_3500
Revises: 20260914_3400
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260914_3500'
down_revision = '20260914_3400'
branch_labels = None
depends_on = None


def upgrade():
    # Certaines installations historiques créent les tables métier via
    # Base.metadata.create_all avant Alembic. La migration doit donc rester
    # sûre même si id_cards n'existe pas encore dans une base fraîche.
    inspector = inspect(op.get_bind())
    if "id_cards" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("id_cards")}
    if "status" not in columns:
        op.add_column('id_cards', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    if "delivered_at" not in columns:
        op.add_column('id_cards', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
    if "lifecycle_note" not in columns:
        op.add_column('id_cards', sa.Column('lifecycle_note', sa.Text(), nullable=True))


def downgrade():
    inspector = inspect(op.get_bind())
    if "id_cards" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("id_cards")}
    if "lifecycle_note" in columns: op.drop_column('id_cards', 'lifecycle_note')
    if "delivered_at" in columns: op.drop_column('id_cards', 'delivered_at')
    if "status" in columns: op.drop_column('id_cards', 'status')
