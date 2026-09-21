"""SIGMA P2 — authoritative RBAC catalog and read/import/export permissions."""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "20260920_6300"
down_revision = "20260920_6200"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    ("students.import", "students", "Importer des élèves"),
    ("students.export", "students", "Exporter les élèves"),
    ("academic.assessments.view", "academic", "Consulter les évaluations"),
    ("academic.assessments.create", "academic", "Créer une évaluation"),
    ("academic.assessments.modify", "academic", "Modifier une évaluation"),
    ("academic.assessments.delete", "academic", "Supprimer une évaluation"),
    ("finance.payments.export", "finance", "Exporter les données financières"),
    ("administration.users.view", "administration", "Consulter les utilisateurs"),
    ("administration.posts.view", "administration", "Consulter les postes"),
    ("administration.permissions.view", "administration", "Consulter le catalogue des permissions"),
    ("administration.ai.use", "administration", "Utiliser l'IA"),
    ("administration.ai.execute", "administration", "Exécuter des actions IA"),
    ("cards.view", "cards", "Consulter les cartes"),
    ("cards.templates.view", "cards", "Consulter les modèles de carte"),
    ("communication.sms.view", "communication", "Consulter les journaux SMS"),
]

PROFILE_GRANTS = {
    "Direction": [
        "students.import", "students.export", "academic.assessments.view", "finance.payments.export",
        "administration.users.view", "administration.posts.view", "administration.permissions.view",
        "administration.ai.use", "administration.ai.execute", "cards.view", "cards.templates.view", "communication.sms.view",
    ],
    "Administration scolaire": [
        "students.import", "students.export", "administration.users.view", "administration.posts.view",
        "administration.permissions.view", "administration.ai.use", "administration.ai.execute",
        "cards.view", "cards.templates.view", "communication.sms.view",
    ],
    "Enseignant": [
        "academic.assessments.view", "academic.assessments.create", "academic.assessments.modify",
    ],
    "Comptabilité": ["finance.payments.export"],
    "Vie scolaire": ["students.export", "cards.view", "cards.templates.view"],
    "Lecture seule": [
        "students.export", "academic.assessments.view", "finance.payments.export", "cards.view", "cards.templates.view", "communication.sms.view",
    ],
}


def _permissions_table():
    return sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("module", sa.String),
        sa.column("label", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )


def upgrade() -> None:
    conn = op.get_bind()
    perms = _permissions_table()
    for code, module, label in NEW_PERMISSIONS:
        exists = conn.execute(sa.select(perms.c.id).where(perms.c.code == code)).first()
        if not exists:
            now = datetime.now(timezone.utc)
            conn.execute(sa.insert(perms).values(code=code, module=module, label=label, created_at=now, updated_at=now))

    posts = sa.table("posts", sa.column("id", sa.Integer), sa.column("name", sa.String))
    pp = sa.table(
        "post_permissions",
        sa.column("post_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
        sa.column("scope", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for post_name, codes in PROFILE_GRANTS.items():
        post_ids = [row[0] for row in conn.execute(sa.select(posts.c.id).where(posts.c.name == post_name)).all()]
        for post_id in post_ids:
            for code in codes:
                perm_id = conn.execute(sa.select(perms.c.id).where(perms.c.code == code)).scalar_one_or_none()
                if not perm_id:
                    continue
                exists = conn.execute(sa.select(pp.c.post_id).where(
                    pp.c.post_id == post_id,
                    pp.c.permission_id == perm_id,
                )).first()
                if not exists:
                    now = datetime.now(timezone.utc)
                    conn.execute(sa.insert(pp).values(post_id=post_id, permission_id=perm_id, scope={}, created_at=now, updated_at=now))


def downgrade() -> None:
    conn = op.get_bind()
    perms = _permissions_table()
    ids = [row[0] for row in conn.execute(sa.select(perms.c.id).where(perms.c.code.in_([x[0] for x in NEW_PERMISSIONS]))).all()]
    if ids:
        pp = sa.table("post_permissions", sa.column("permission_id", sa.Integer))
        conn.execute(sa.delete(pp).where(pp.c.permission_id.in_(ids)))
        conn.execute(sa.delete(perms).where(perms.c.id.in_(ids)))
