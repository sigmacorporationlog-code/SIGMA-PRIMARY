"""SIGMA V4.18 — onboarding établissement."""
from alembic import op
import sqlalchemy as sa
revision='20260915_4900'; down_revision='20260915_4800'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('school_onboardings',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('school_id',sa.Integer(),sa.ForeignKey('schools.id'),nullable=False,unique=True),
        sa.Column('status',sa.String(30),nullable=False,server_default='draft'),
        sa.Column('current_step',sa.String(50),nullable=False,server_default='school'),
        sa.Column('completed_steps',sa.JSON(),nullable=False,server_default='[]'),
        sa.Column('checklist',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('is_completed',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('created_at',sa.DateTime(timezone=True)), sa.Column('updated_at',sa.DateTime(timezone=True)))

def downgrade(): op.drop_table('school_onboardings')
