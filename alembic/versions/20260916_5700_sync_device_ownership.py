"""Bind offline sync devices to the registering user."""
from alembic import op
import sqlalchemy as sa

revision = "20260916_5700"
down_revision = "20260916_5600"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sync_devices", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_sync_devices_owner_user_id", ["owner_user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_sync_devices_owner_user_id_users", "users", ["owner_user_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("sync_devices", recreate="always") as batch_op:
        batch_op.drop_constraint("fk_sync_devices_owner_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_sync_devices_owner_user_id")
        batch_op.drop_column("owner_user_id")
