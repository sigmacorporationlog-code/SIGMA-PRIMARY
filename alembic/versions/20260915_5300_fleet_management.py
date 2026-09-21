"""SIGMA V4.40 — fleet inventory and safe rollout state."""
from alembic import op
import sqlalchemy as sa
revision='20260915_5300'
down_revision='20260915_5200'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('fleet_installations',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('school_id',sa.Integer(),sa.ForeignKey('schools.id'),nullable=False),
        sa.Column('instance_id',sa.String(120),nullable=False),
        sa.Column('installed_version',sa.String(40),nullable=False,server_default='unknown'),
        sa.Column('channel',sa.String(30),nullable=False,server_default='commercial'),
        sa.Column('status',sa.String(30),nullable=False,server_default='unknown'),
        sa.Column('last_seen_at',sa.DateTime(timezone=True)),
        sa.Column('last_backup_at',sa.DateTime(timezone=True)),
        sa.Column('last_sync_at',sa.DateTime(timezone=True)),
        sa.Column('last_health',sa.String(30),nullable=False,server_default='unknown'),
        sa.Column('disk_free_bytes',sa.BigInteger()),
        sa.Column('metadata_json',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('created_at',sa.DateTime(timezone=True)), sa.Column('updated_at',sa.DateTime(timezone=True)),
        sa.UniqueConstraint('school_id',name='uq_fleet_installation_school'), sa.UniqueConstraint('instance_id',name='uq_fleet_installation_instance'))
    op.create_index('ix_fleet_installations_school_id','fleet_installations',['school_id'])
    op.create_index('ix_fleet_installations_instance_id','fleet_installations',['instance_id'])
    op.create_index('ix_fleet_installations_status','fleet_installations',['status'])
    op.create_index('ix_fleet_installations_last_seen_at','fleet_installations',['last_seen_at'])
    op.create_table('fleet_rollouts',
        sa.Column('id',sa.Integer(),primary_key=True), sa.Column('target_version',sa.String(40),nullable=False),
        sa.Column('channel',sa.String(30),nullable=False,server_default='commercial'), sa.Column('strategy',sa.String(30),nullable=False,server_default='canary'),
        sa.Column('status',sa.String(30),nullable=False,server_default='planned'), sa.Column('canary_percent',sa.Integer(),nullable=False,server_default='10'),
        sa.Column('max_failure_percent',sa.Integer(),nullable=False,server_default='10'), sa.Column('started_at',sa.DateTime(timezone=True)),
        sa.Column('completed_at',sa.DateTime(timezone=True)), sa.Column('metadata_json',sa.JSON(),nullable=False,server_default='{}'),
        sa.Column('created_at',sa.DateTime(timezone=True)), sa.Column('updated_at',sa.DateTime(timezone=True)))
    op.create_index('ix_fleet_rollouts_target_version','fleet_rollouts',['target_version'])
    op.create_index('ix_fleet_rollouts_status','fleet_rollouts',['status'])

def downgrade():
    op.drop_index('ix_fleet_rollouts_status',table_name='fleet_rollouts'); op.drop_index('ix_fleet_rollouts_target_version',table_name='fleet_rollouts'); op.drop_table('fleet_rollouts')
    op.drop_index('ix_fleet_installations_last_seen_at',table_name='fleet_installations'); op.drop_index('ix_fleet_installations_status',table_name='fleet_installations'); op.drop_index('ix_fleet_installations_instance_id',table_name='fleet_installations'); op.drop_index('ix_fleet_installations_school_id',table_name='fleet_installations'); op.drop_table('fleet_installations')
