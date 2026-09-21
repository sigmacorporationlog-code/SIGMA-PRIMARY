"""SIGMA 1.7 — sync devices, operation journal and entity versions."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_1700"
down_revision = "20260913_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sync_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False, server_default="client"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ip", sa.String(64)),
        sa.Column("app_version", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False, server_default="online"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "device_id", name="uq_sync_device_school_device"),
    )
    op.create_index("ix_sync_devices_school_id", "sync_devices", ["school_id"])
    op.create_index("ix_sync_devices_device_id", "sync_devices", ["device_id"])

    op.create_table(
        "sync_entity_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "entity_type", "entity_id", name="uq_sync_entity_version"),
    )
    op.create_index("ix_sync_entity_versions_school_id", "sync_entity_versions", ["school_id"])

    op.create_table(
        "sync_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation_id", sa.String(100), nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("operation_type", sa.String(20), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("server_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text()),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("operation_id", name="uq_sync_operation_id"),
    )
    op.create_index("ix_sync_operations_school_id", "sync_operations", ["school_id"])
    op.create_index("ix_sync_operations_operation_id", "sync_operations", ["operation_id"])
    op.create_index("ix_sync_operations_device_id", "sync_operations", ["device_id"])
    op.create_index("ix_sync_operations_status", "sync_operations", ["status"])


def downgrade():
    op.drop_table("sync_operations")
    op.drop_table("sync_entity_versions")
    op.drop_table("sync_devices")
