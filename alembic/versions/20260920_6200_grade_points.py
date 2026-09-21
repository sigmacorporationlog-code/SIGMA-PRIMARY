"""SIGMA V4.46.0 H3 — configurable letter grades and GPA points."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6200"
down_revision = "20260920_6100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rating_scales", sa.Column("grade_point", sa.Numeric(4, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("rating_scales", "grade_point")
