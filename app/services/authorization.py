"""
Moteur d'habilitation de SIGMA.

Pour chaque requête sensible, on répond à :
  QUI ? (user)  QUOI ? (permission_code)  SUR QUELLES DONNÉES / QUELLE CLASSE /
  QUELLE MATIÈRE ? (context)  À QUEL MOMENT ? (délégations avec dates)

Un "scope" stocké sur un PostPermission (ou une Delegation) est un dict JSON.
Une clé absente ou une valeur null dans le scope = pas de restriction sur ce
critère. Le scope "gagne" si TOUTES ses clés définies correspondent au
contexte de la requête.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models.security import User, UserPost, PostPermission, Permission, Delegation


class PermissionDenied(Exception):
    def __init__(self, permission_code: str):
        self.permission_code = permission_code
        super().__init__(f"Permission refusée: {permission_code}")


def _scope_matches(scope: dict, context: dict) -> bool:
    """Un scope vide autorise tout. Sinon chaque clé définie du scope doit
    correspondre à la valeur du contexte (ou context['own_user_id'] pour
    own_records_only)."""
    if not scope:
        return True
    for key, expected in scope.items():
        if expected is None:
            continue
        if key == "own_records_only":
            if expected and context.get("owner_id") != context.get("requesting_user_id"):
                return False
            continue
        if context.get(key) != expected:
            return False
    return True


def user_has_permission(
    db: Session,
    user: User,
    permission_code: str,
    context: dict | None = None,
) -> bool:
    """Retourne True si l'utilisateur détient la permission, via un de ses
    postes ou via une délégation active, en respectant le périmètre."""
    if user.is_superadmin:
        return True

    context = dict(context or {})
    context.setdefault("requesting_user_id", user.id)

    permission = db.query(Permission).filter(Permission.code == permission_code).first()
    if permission is None:
        return False

    # 1. Permissions via les postes de l'utilisateur
    # Défense en profondeur : une association UserPost ou une délégation
    # mal formée ne doit jamais permettre de traverser le tenant.
    post_ids = [
        up.post_id
        for up in (
            db.query(UserPost)
            .join(UserPost.post)
            .filter(UserPost.user_id == user.id)
            .all()
        )
        if up.post is not None and up.post.school_id == user.school_id
    ]
    if post_ids:
        post_perms = (
            db.query(PostPermission)
            .filter(PostPermission.post_id.in_(post_ids), PostPermission.permission_id == permission.id)
            .all()
        )
        for pp in post_perms:
            if _scope_matches(pp.scope or {}, context):
                return True

    # 2. Délégations temporaires actives
    today = date.today()
    delegations = (
        db.query(Delegation)
        .filter(
            Delegation.granted_to_id == user.id,
            Delegation.school_id == user.school_id,
            Delegation.permission_id == permission.id,
            Delegation.is_revoked.is_(False),
            Delegation.start_date <= today,
            Delegation.end_date >= today,
        )
        .all()
    )
    for dele in delegations:
        if _scope_matches(dele.scope or {}, context):
            return True

    return False


def require_permission(db: Session, user: User, permission_code: str, context: dict | None = None) -> None:
    if not user_has_permission(db, user, permission_code, context):
        raise PermissionDenied(permission_code)


def user_can_grant_permission(db: Session, user: User, permission_code: str) -> bool:
    """Retourne True si l'acteur peut transmettre une permission sans
    augmenter son propre niveau de privilège. Une délégation temporaire ou
    une permission à périmètre restreint ne peut pas servir de tremplin pour
    créer une autorisation plus large. Le superadmin reste l'autorité
    centrale.
    """
    if user.is_superadmin:
        return True
    permission = db.query(Permission).filter(Permission.code == permission_code).first()
    if permission is None:
        return False
    post_ids = [
        up.post_id
        for up in db.query(UserPost).join(UserPost.post).filter(UserPost.user_id == user.id).all()
        if up.post is not None and up.post.school_id == user.school_id
    ]
    if not post_ids:
        return False
    return db.query(PostPermission).filter(
        PostPermission.post_id.in_(post_ids),
        PostPermission.permission_id == permission.id,
        PostPermission.scope == {},
    ).first() is not None
