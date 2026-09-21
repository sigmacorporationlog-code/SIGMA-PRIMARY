"""SIGMA 2.1 — synchronisation des inscriptions hors ligne."""
from alembic import op

revision = "20260913_2100"
down_revision = "20260913_2000"
branch_labels = None
depends_on = None


def upgrade():
    # v2.1 ne nécessite pas de nouvelle table : les inscriptions utilisent
    # class_memberships et le journal/identité de synchronisation existants.
    return None


def downgrade():
    return None
