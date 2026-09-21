"""SIGMA V4.46 — configurable student matricule sequence."""
from alembic import op
import sqlalchemy as sa

revision = "20260916_5500"
down_revision = "20260916_5400"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("schools") as batch:
        batch.add_column(sa.Column("matricule_strategy", sa.String(length=40), nullable=False, server_default="year_sequence"))
        batch.add_column(sa.Column("matricule_template", sa.String(length=80), nullable=False, server_default="{YY}{SEQ:05}"))
        batch.add_column(sa.Column("matricule_next_sequence", sa.Integer(), nullable=False, server_default="0"))
        batch.alter_column("matricule_strategy", server_default=None)
        batch.alter_column("matricule_template", server_default=None)
        batch.alter_column("matricule_next_sequence", server_default=None)

def downgrade():
    with op.batch_alter_table("schools") as batch:
        batch.drop_column("matricule_next_sequence")
        batch.drop_column("matricule_template")
        batch.drop_column("matricule_strategy")
