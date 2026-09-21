"""Configurable GPA calculation mode; preserves historical overall-scale behavior."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6330"
down_revision = "20260920_6320"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "evaluation_frameworks",
        sa.Column("gpa_mode", sa.String(30), nullable=False, server_default="overall_scale"),
    )


def downgrade():
    op.drop_column("evaluation_frameworks", "gpa_mode")
