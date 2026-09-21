"""billing automation and subscription grace controls

Revision ID: 20260914_4200
Revises: 20260914_4100
"""
from alembic import op
import sqlalchemy as sa

revision = '20260914_4200'
down_revision = '20260914_4100'
branch_labels = None
depends_on = None


def upgrade():
    # Use direct ALTER/INDEX operations rather than SQLite batch reflection:
    # SIGMA's legacy core tables (schools, etc.) are created by the application
    # bootstrap and are intentionally not all represented in Alembic.
    op.add_column('school_subscriptions', sa.Column('grace_period_days', sa.Integer(), nullable=False, server_default='7'))
    op.add_column('school_subscriptions', sa.Column('suspended_on', sa.Date(), nullable=True))
    op.add_column('subscription_payments', sa.Column('external_event_id', sa.String(length=150), nullable=True))
    op.create_index('ix_subscription_payments_external_event_id', 'subscription_payments', ['external_event_id'], unique=True)
    op.create_index('uq_subscription_invoice_period', 'subscription_invoices', ['school_id', 'period_start', 'period_end'], unique=True)


def downgrade():
    op.drop_index('uq_subscription_invoice_period', table_name='subscription_invoices')
    op.drop_index('ix_subscription_payments_external_event_id', table_name='subscription_payments')
    op.drop_column('subscription_payments', 'external_event_id')
    op.drop_column('school_subscriptions', 'suspended_on')
    op.drop_column('school_subscriptions', 'grace_period_days')
