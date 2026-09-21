"""Use NUMERIC for academic/evaluation scores, coefficients and percentages."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6320"
down_revision = "20260920_6310"
branch_labels = None
depends_on = None

NUMERIC_SCORE = sa.Numeric(10, 4)
NUMERIC_PERCENT = sa.Numeric(7, 4)

TARGETS = {
    "subjects": {"default_coefficient": NUMERIC_SCORE},
    "teacher_assignments": {"coefficient": NUMERIC_SCORE},
    "assessments": {"max_score": NUMERIC_SCORE, "coefficient": NUMERIC_SCORE},
    "grades": {"score": NUMERIC_SCORE},
    "grade_state_history": {"old_score": NUMERIC_SCORE, "new_score": NUMERIC_SCORE},
    "report_cards": {"general_average": NUMERIC_SCORE},
    "honor_board_entries": {"score": NUMERIC_SCORE},
    "evaluation_domains": {"weight": NUMERIC_SCORE},
    "evaluation_criteria": {"max_score": NUMERIC_SCORE, "weight": NUMERIC_SCORE},
    "rating_scales": {"min_percent": NUMERIC_PERCENT, "max_percent": NUMERIC_PERCENT},
    "evaluation_activities": {"max_score": NUMERIC_SCORE, "coefficient": NUMERIC_SCORE},
    "evaluation_appreciation_rules": {"min_percent": NUMERIC_PERCENT, "max_percent": NUMERIC_PERCENT},
    "evaluation_results": {"score": NUMERIC_SCORE, "max_score": NUMERIC_SCORE},
}


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    for table, columns in TARGETS.items():
        existing = {col["name"]: col for col in inspector.get_columns(table)}
        for column, numeric_type in columns.items():
            if column not in existing:
                continue
            current_type = existing[column]["type"]
            if isinstance(current_type, sa.Numeric):
                continue
            if dialect == "sqlite":
                with op.batch_alter_table(table) as batch_op:
                    batch_op.alter_column(column, existing_type=current_type, type_=numeric_type)
            else:
                op.alter_column(
                    table,
                    column,
                    existing_type=current_type,
                    type_=numeric_type,
                    postgresql_using=f"CAST({column} AS NUMERIC)",
                )
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    for table, columns in TARGETS.items():
        existing = {col["name"]: col for col in inspector.get_columns(table)}
        for column, numeric_type in columns.items():
            if column not in existing or not isinstance(existing[column]["type"], sa.Numeric):
                continue
            float_type = sa.Float()
            if dialect == "sqlite":
                with op.batch_alter_table(table) as batch_op:
                    batch_op.alter_column(column, existing_type=existing[column]["type"], type_=float_type)
            else:
                op.alter_column(
                    table,
                    column,
                    existing_type=existing[column]["type"],
                    type_=float_type,
                    postgresql_using=f"CAST({column} AS DOUBLE PRECISION)",
                )
            inspector = sa.inspect(bind)
