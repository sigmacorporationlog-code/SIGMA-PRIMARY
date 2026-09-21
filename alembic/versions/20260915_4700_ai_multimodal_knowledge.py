"""SIGMA V4.13 — provenance et activation des versions documentaires."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_4700"
down_revision = "20260915_4600"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Provenance fine des passages : page, paragraphe ou unité source.
    # JSON permet de rester compatible SQLite/PostgreSQL sans changement lourd.
    # Les colonnes ne sont pas nécessaires : la provenance est stockée dans
    # metadata_json de chaque chunk, donc cette migration documente la version
    # et laisse le schéma relationnel stable.
    return None


def downgrade() -> None:
    return None
