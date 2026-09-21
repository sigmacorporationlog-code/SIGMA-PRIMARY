"""SIGMA V3.8 Cloud commercial, licence et audit chain"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260914_3800"
down_revision = "20260914_3700"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "school_subscriptions" not in tables:
        op.create_table(
            "school_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False, unique=True),
            sa.Column("plan_code", sa.String(50), nullable=False, server_default="standard"),
            sa.Column("status", sa.String(30), nullable=False, server_default="trial"),
            sa.Column("starts_on", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
            sa.Column("ends_on", sa.Date(), nullable=True),
            sa.Column("max_users", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("max_students", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("license_key_hash", sa.String(128), nullable=True),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "cloud_events" not in tables:
        op.create_table(
            "cloud_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "audit_logs" in tables:
        columns = {c["name"] for c in inspector.get_columns("audit_logs")}
        if "previous_hash" not in columns:
            op.add_column("audit_logs", sa.Column("previous_hash", sa.String(64), nullable=True))
        if "entry_hash" not in columns:
            op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "audit_logs" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("audit_logs")}
        if "entry_hash" in columns:
            op.drop_column("audit_logs", "entry_hash")
        if "previous_hash" in columns:
            op.drop_column("audit_logs", "previous_hash")
    if "cloud_events" in inspector.get_table_names():
        op.drop_table("cloud_events")
    if "school_subscriptions" in inspector.get_table_names():
        op.drop_table("school_subscriptions")
