"""Harden honor board history with uniqueness and lookup indexes."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6310"
down_revision = "20260920_6300"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    uniques = {c.get("name") for c in inspector.get_unique_constraints("honor_board_entries")}
    indexes = {i.get("name") for i in inspector.get_indexes("honor_board_entries")}
    if "uq_honor_board_rule_student_period" not in uniques:
        with op.batch_alter_table("honor_board_entries") as batch_op:
            batch_op.create_unique_constraint("uq_honor_board_rule_student_period", ["rule_id", "student_id", "academic_period_id"])
    if "ix_honor_board_entries_rule_period" not in indexes:
        op.create_index("ix_honor_board_entries_rule_period", "honor_board_entries", ["rule_id", "academic_period_id", "rank"])


def downgrade():
    op.drop_index("ix_honor_board_entries_rule_period", table_name="honor_board_entries")
    with op.batch_alter_table("honor_board_entries") as batch_op:
        batch_op.drop_constraint("uq_honor_board_rule_student_period", type_="unique")
