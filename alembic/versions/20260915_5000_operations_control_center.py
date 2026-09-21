"""SIGMA V4.19 — Control Center operations and incidents."""
from alembic import op
import sqlalchemy as sa
revision='20260915_5000'; down_revision='20260915_4900'; branch_labels=None; depends_on=None

def upgrade():
    op.create_table('platform_incidents',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('school_id',sa.Integer(),sa.ForeignKey('schools.id'),nullable=True),
        sa.Column('severity',sa.String(20),nullable=False,server_default='medium'), sa.Column('status',sa.String(20),nullable=False,server_default='open'),
        sa.Column('category',sa.String(80),nullable=False), sa.Column('title',sa.String(180),nullable=False), sa.Column('description',sa.Text()),
        sa.Column('detected_at',sa.DateTime(timezone=True),nullable=False), sa.Column('resolved_at',sa.DateTime(timezone=True)),
        sa.Column('detected_by_user_id',sa.Integer(),sa.ForeignKey('users.id')), sa.Column('resolved_by_user_id',sa.Integer(),sa.ForeignKey('users.id')),
        sa.Column('metadata_json',sa.JSON(),nullable=False,server_default='{}'), sa.Column('created_at',sa.DateTime(timezone=True)), sa.Column('updated_at',sa.DateTime(timezone=True)))
    op.create_index('ix_platform_incidents_school_id','platform_incidents',['school_id']); op.create_index('ix_platform_incidents_severity','platform_incidents',['severity']); op.create_index('ix_platform_incidents_status','platform_incidents',['status']); op.create_index('ix_platform_incidents_category','platform_incidents',['category'])
    op.create_table('platform_metric_snapshots',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('period_key',sa.String(30),nullable=False), sa.Column('schools_count',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('active_schools',sa.Integer(),nullable=False,server_default='0'), sa.Column('users_count',sa.Integer(),nullable=False,server_default='0'), sa.Column('students_count',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('open_incidents',sa.Integer(),nullable=False,server_default='0'), sa.Column('storage_bytes',sa.Integer(),nullable=False,server_default='0'), sa.Column('metadata_json',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('created_at',sa.DateTime(timezone=True)), sa.Column('updated_at',sa.DateTime(timezone=True)))
    op.create_index('ix_platform_metric_snapshots_period_key','platform_metric_snapshots',['period_key'])

def downgrade():
    op.drop_table('platform_metric_snapshots'); op.drop_table('platform_incidents')
