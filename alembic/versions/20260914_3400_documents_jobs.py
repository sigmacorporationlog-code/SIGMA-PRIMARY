"""SIGMA V3 documents and bulk export jobs"""
from alembic import op
import sqlalchemy as sa

revision = '20260914_3400'
down_revision = '20260914_3300'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('document_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_path', sa.Text()),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('finished_at', sa.DateTime(timezone=True)))
    op.create_index('ix_document_jobs_school_id', 'document_jobs', ['school_id'])
    op.create_index('ix_document_jobs_status', 'document_jobs', ['status'])

def downgrade():
    op.drop_index('ix_document_jobs_status', table_name='document_jobs')
    op.drop_index('ix_document_jobs_school_id', table_name='document_jobs')
    op.drop_table('document_jobs')
