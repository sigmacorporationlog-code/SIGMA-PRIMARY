"""Persist honor-board scope and validation audit snapshot."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6340"
down_revision = "20260920_6330"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("honor_board_entries")}
    add = []
    if "class_id" not in cols:
        add.append(sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("classes.id", name="fk_honor_board_entries_class_id_classes"),
            nullable=True,
        ))
    if "unjustified_absences" not in cols:
        add.append(sa.Column("unjustified_absences", sa.Integer(), nullable=False, server_default="0"))
    if "validated_at" not in cols:
        add.append(sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    if "validated_by_id" not in cols:
        add.append(sa.Column(
            "validated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", name="fk_honor_board_entries_validated_by_users"),
            nullable=True,
        ))
    if add:
        with op.batch_alter_table("honor_board_entries") as batch:
            for column in add:
                batch.add_column(column)

    # Backfill the historical class snapshot where a current membership for the
    # same academic year can be determined. Old entries remain nullable when
    # no unambiguous historical membership exists.
    if "class_id" not in cols:
        op.execute(sa.text(
            "UPDATE honor_board_entries "
            "SET class_id = ("
            "SELECT cm.class_id FROM class_memberships cm "
            "JOIN academic_periods ap ON ap.id = honor_board_entries.academic_period_id "
            "WHERE cm.student_id = honor_board_entries.student_id "
            "AND cm.academic_year_id = ap.academic_year_id "
            "AND cm.left_at IS NULL "
            "ORDER BY cm.id LIMIT 1) "
            "WHERE class_id IS NULL"
        ))

    if "ix_honor_board_entries_rule_period_class" not in {i["name"] for i in inspector.get_indexes("honor_board_entries")}:
        op.create_index(
            "ix_honor_board_entries_rule_period_class",
            "honor_board_entries",
            ["rule_id", "academic_period_id", "class_id", "rank"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("honor_board_entries")}
    if "ix_honor_board_entries_rule_period_class" in indexes:
        op.drop_index("ix_honor_board_entries_rule_period_class", table_name="honor_board_entries")
    cols = {c["name"] for c in inspector.get_columns("honor_board_entries")}
    drop = [name for name in ("validated_by_id", "validated_at", "unjustified_absences", "class_id") if name in cols]
    if drop:
        with op.batch_alter_table("honor_board_entries") as batch:
            for name in drop:
                batch.drop_column(name)
