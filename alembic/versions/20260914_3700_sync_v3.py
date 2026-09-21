"""SIGMA V3 Cloud/Offline/Sync health state"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_3700"
down_revision = "20260914_3500"
branch_labels = None
depends_on = None

def upgrade():
    inspector = inspect(op.get_bind())
    if "sync_devices" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("sync_devices")}
    if "last_sync_at" not in columns:
        op.add_column("sync_devices", sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))
    if "last_sync_status" not in columns:
        op.add_column("sync_devices", sa.Column("last_sync_status", sa.String(length=30), nullable=True))
    if "last_sync_error" not in columns:
        op.add_column("sync_devices", sa.Column("last_sync_error", sa.Text(), nullable=True))

def downgrade():
    inspector = inspect(op.get_bind())
    if "sync_devices" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("sync_devices")}
    for name in ("last_sync_error", "last_sync_status", "last_sync_at"):
        if name in columns:
            op.drop_column("sync_devices", name)
