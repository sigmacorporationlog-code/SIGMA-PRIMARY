"""SIGMA V4.48 — destinations cloud de sauvegarde (Google Drive, OneDrive, Dropbox)."""
from alembic import op
import sqlalchemy as sa

revision = "20260919_5900"
down_revision = "20260918_5800"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cloud_backup_destinations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("encrypted_access_token", sa.String(length=2000), nullable=False),
        sa.Column("encrypted_refresh_token", sa.String(length=2000), nullable=True),
        sa.Column("folder_path", sa.String(length=300), nullable=False, server_default="/SIGMA"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cloud_backup_destinations_school_id", "cloud_backup_destinations", ["school_id"])


def downgrade():
    op.drop_index("ix_cloud_backup_destinations_school_id", table_name="cloud_backup_destinations")
    op.drop_table("cloud_backup_destinations")
