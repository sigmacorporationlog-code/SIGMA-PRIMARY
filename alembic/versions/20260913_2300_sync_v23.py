"""sync v2.3 academic grade protocol

Revision ID: 20260913_2300
Revises: 20260913_2200
"""
from alembic import op

revision = "20260913_2300"
down_revision = "20260913_2200"
branch_labels = None
depends_on = None


def upgrade():
    # v2.3 ajoute uniquement des handlers métier ; aucune nouvelle table n'est requise.
    return None


def downgrade():
    return None
