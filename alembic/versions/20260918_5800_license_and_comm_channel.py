"""SIGMA V4.47 — canal de communication par défaut de l'établissement."""
from alembic import op
import sqlalchemy as sa

revision = "20260918_5800"
down_revision = "20260916_5700"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("schools") as batch:
        batch.add_column(sa.Column("communication_channel_default", sa.String(length=20), nullable=False, server_default="sms"))
        batch.alter_column("communication_channel_default", server_default=None)


def downgrade():
    with op.batch_alter_table("schools") as batch:
        batch.drop_column("communication_channel_default")
