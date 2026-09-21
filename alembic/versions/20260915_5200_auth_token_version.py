"""SIGMA V4.25 — Token revocation versioning."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_5200"
down_revision = "20260915_5100"
branch_labels = None
depends_on = None


def upgrade():
    # Batch mode keeps the migration compatible with SQLite while preserving
    # the same final schema on PostgreSQL/MySQL.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"))
        batch.alter_column("token_version", server_default=None)


def downgrade():
    op.drop_column("users", "token_version")
