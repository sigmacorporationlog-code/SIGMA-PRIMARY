"""SIGMA V4.46 — atomic badge numbering."""
from alembic import op
import sqlalchemy as sa

revision = "20260916_5600"
down_revision = "20260916_5500"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("schools") as batch:
        batch.add_column(sa.Column("badge_next_sequence", sa.Integer(), nullable=False, server_default="0"))
        batch.alter_column("badge_next_sequence", server_default=None)

def downgrade():
    with op.batch_alter_table("schools") as batch:
        batch.drop_column("badge_next_sequence")
