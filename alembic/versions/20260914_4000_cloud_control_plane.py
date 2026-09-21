"""SIGMA V4 Cloud control plane, plans and usage snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_4000"
down_revision = "20260914_3800"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "cloud_plans" not in tables:
        op.create_table(
            "cloud_plans",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("monthly_price_xaf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("annual_price_xaf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_users", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("max_students", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "cloud_usage_snapshots" not in tables:
        op.create_table(
            "cloud_usage_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
            sa.Column("period_key", sa.String(20), nullable=False),
            sa.Column("users_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("students_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("api_requests", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sync_operations", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("school_id", "period_key", name="uq_cloud_usage_school_period"),
        )
        op.create_index("ix_cloud_usage_snapshots_school_id", "cloud_usage_snapshots", ["school_id"])
        op.create_index("ix_cloud_usage_snapshots_period_key", "cloud_usage_snapshots", ["period_key"])


def downgrade():
    bind = op.get_bind(); inspector = inspect(bind); tables = set(inspector.get_table_names())
    if "cloud_usage_snapshots" in tables:
        op.drop_table("cloud_usage_snapshots")
    if "cloud_plans" in tables:
        op.drop_table("cloud_plans")
