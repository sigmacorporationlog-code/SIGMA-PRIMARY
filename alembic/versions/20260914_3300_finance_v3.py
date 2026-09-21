"""SIGMA V3 finance foundation"""
from alembic import op
import sqlalchemy as sa

revision = '20260914_3300'
down_revision = '20260914_3100'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('mobile_money_configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=False),
        sa.Column('provider', sa.String(30), nullable=False),
        sa.Column('merchant_name', sa.String(150)), sa.Column('merchant_code', sa.String(100)),
        sa.Column('api_base_url', sa.String(500)), sa.Column('credentials_ref', sa.Text()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True)), sa.Column('updated_at', sa.DateTime(timezone=True)))
    op.create_table('payment_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=False),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payments.id')),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('provider', sa.String(30), nullable=False), sa.Column('external_reference', sa.String(150), unique=True),
        sa.Column('payer_phone', sa.String(30)), sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='XAF'),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'), sa.Column('provider_message', sa.Text()),
        sa.Column('processed_at', sa.DateTime(timezone=True)), sa.Column('created_at', sa.DateTime(timezone=True)), sa.Column('updated_at', sa.DateTime(timezone=True)))
    op.create_table('finance_reminders',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=False),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id'), nullable=False), sa.Column('channel', sa.String(30), nullable=False),
        sa.Column('recipient', sa.String(150)), sa.Column('status', sa.String(30), nullable=False, server_default='queued'),
        sa.Column('message', sa.Text()), sa.Column('sent_at', sa.DateTime(timezone=True)), sa.Column('created_at', sa.DateTime(timezone=True)), sa.Column('updated_at', sa.DateTime(timezone=True)))

def downgrade():
    op.drop_table('finance_reminders'); op.drop_table('payment_transactions'); op.drop_table('mobile_money_configurations')
