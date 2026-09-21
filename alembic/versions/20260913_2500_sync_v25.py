"""v2.5: fiabilisation de la reprise des lots de synchronisation.

Revision ID: 20260913_2500
Revises: 20260913_2400
"""
from alembic import op

revision = "20260913_2500"
down_revision = "20260913_2400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # v2.5 n'ajoute pas de colonne : les endpoints de reprise et le type
    # student_guardian exploitent les structures de synchronisation existantes.
    return None


def downgrade() -> None:
    return None
