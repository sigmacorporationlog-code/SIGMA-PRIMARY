"""SIGMA 2.0 — identités client/serveur pour créations offline."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_2000"
down_revision = "20260913_1700"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sync_entity_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("client_entity_id", sa.String(100), nullable=False),
        sa.Column("server_entity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "entity_type", "client_entity_id", name="uq_sync_identity_client"),
        sa.UniqueConstraint("school_id", "entity_type", "server_entity_id", name="uq_sync_identity_server"),
    )
    op.create_index("ix_sync_entity_identities_school_id", "sync_entity_identities", ["school_id"])
    op.create_index("ix_sync_entity_identities_device_id", "sync_entity_identities", ["device_id"])


def downgrade():
    op.drop_table("sync_entity_identities")
