"""v2.4: synchronisation contrôlée des transitions d'état des notes.

Revision ID: 20260913_2400
Revises: 20260913_2300
"""
from alembic import op

revision = "20260913_2400"
down_revision = "20260913_2300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # v2.4 ne modifie pas le schéma : le protocole exploite les tables existantes.
    return None


def downgrade() -> None:
    return None
