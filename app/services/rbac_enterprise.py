"""RBAC Enterprise: profils de postes standardisés et contrôle des attributions.

Les postes restent configurables par établissement. Les profils ci-dessous sont
uniquement des modèles de départ; aucune permission n'est implicitement accordée
à un utilisateur sans attribution explicite du poste.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.security import User, Post, Permission, PostPermission, UserPost
from app.services.authorization import user_can_grant_permission

ROLE_PROFILES = {
    "direction": {
        "name": "Direction",
        "description": "Pilotage général de l'établissement.",
        "permissions": [
            "students.view", "students.create", "students.modify", "students.archive", "students.transfer", "students.export",
            "academic.grades.view", "academic.assessments.view", "academic.report_cards.generate", "academic.report_cards.publish",
            "finance.payments.view", "finance.payments.print_receipt", "finance.cash.view", "finance.payments.export",
            "administration.users.view", "administration.users.create", "administration.users.modify",
            "administration.posts.view", "administration.posts.create", "administration.permissions.view", "administration.permissions.modify",
            "administration.audit.view", "administration.system.view", "administration.classes.create", "administration.settings.modify",
            "administration.operations.view", "administration.operations.execute", "administration.backup.view", "administration.backup.create",
            "administration.ai.use", "administration.ai.execute", "cards.view", "cards.templates.view", "cards.templates.modify",
            "communication.sms.view", "communication.sms.send",
        ],
    },
    "administration": {
        "name": "Administration scolaire",
        "description": "Gestion administrative des élèves et des utilisateurs.",
        "permissions": [
            "students.view", "students.create", "students.modify", "students.archive", "students.transfer", "students.import", "students.export",
            "administration.users.view", "administration.users.create", "administration.users.modify",
            "administration.posts.view", "administration.audit.view", "administration.settings.modify", "administration.classes.create",
            "administration.system.view", "administration.operations.view", "administration.operations.execute", "administration.backup.view", "administration.backup.create",
            "administration.permissions.view", "cards.view", "cards.templates.view", "cards.templates.modify",
            "communication.sms.view", "communication.sms.send",
        ],
    },
    "enseignant": {
        "name": "Enseignant",
        "description": "Travail pédagogique et suivi des classes.",
        "permissions": [
            "students.view", "academic.grades.view", "academic.grades.enter", "academic.assessments.view", "academic.assessments.create", "academic.assessments.modify",
            "evaluation.results.view", "evaluation.results.enter",
        ],
    },
    "comptabilite": {
        "name": "Comptabilité",
        "description": "Encaissement et suivi financier.",
        "permissions": [
            "finance.payments.view", "finance.payments.record", "finance.payments.modify", "finance.payments.print_receipt", "finance.payments.export",
            "finance.cash.view", "finance.cash.close",
        ],
    },
    "vie_scolaire": {
        "name": "Vie scolaire",
        "description": "Suivi administratif et vie scolaire.",
        "permissions": ["students.view", "students.modify", "students.archive", "students.transfer", "students.export", "cards.view", "cards.templates.view"],
    },
    "lecture_seule": {
        "name": "Lecture seule",
        "description": "Accès de consultation sans modification.",
        "permissions": ["students.view", "students.export", "academic.grades.view", "academic.assessments.view", "finance.payments.view", "finance.payments.export", "evaluation.results.view", "cards.view", "cards.templates.view", "communication.sms.view"],
    },
}



def ensure_profile(db: Session, school_id: int, profile_code: str) -> Post:
    spec = ROLE_PROFILES.get(profile_code)
    if not spec:
        raise HTTPException(status_code=404, detail="Profil RBAC inconnu")
    post = db.query(Post).filter(Post.school_id == school_id, Post.name == spec["name"]).first()
    if post is None:
        post = Post(school_id=school_id, name=spec["name"], description=spec["description"])
        db.add(post); db.flush()
    for code in spec["permissions"]:
        permission = db.query(Permission).filter(Permission.code == code).first()
        if permission and not db.query(PostPermission).filter_by(post_id=post.id, permission_id=permission.id, scope={}).first():
            db.add(PostPermission(post_id=post.id, permission_id=permission.id, scope={}))
    db.commit(); db.refresh(post)
    return post


def profile_catalog():
    return [{"code": code, "name": spec["name"], "description": spec["description"], "permission_count": len(spec["permissions"])}
            for code, spec in ROLE_PROFILES.items()]


def bootstrap_first_administrator(db: Session, school_id: int, actor: User, profile_code: str = "direction") -> Post | None:
    """Attribue un profil d'amorçage au tout premier compte d'un établissement.

    Sans cela, l'initialisation d'un établissement neuf est impossible : le
    contrôle de délégation de `assign_profile` exige que l'acteur détienne déjà
    les permissions qu'il transmet, or aucun poste n'existe encore. Cette
    fonction n'est donc PAS un contournement du durcissement : elle refuse dès
    qu'une attribution de poste existe déjà dans l'établissement, ce qui la rend
    inutilisable comme vecteur d'élévation de privilèges par la suite.
    """
    if actor.school_id != school_id and not actor.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé à cet établissement")
    already_assigned = (
        db.query(UserPost)
        .join(UserPost.post)
        .filter(Post.school_id == school_id)
        .first()
    )
    if already_assigned is not None:
        return None
    post = ensure_profile(db, school_id, profile_code)
    db.add(UserPost(user_id=actor.id, post_id=post.id))
    db.commit()
    return post


def assign_profile(db: Session, actor: User, user_id: int, profile_code: str) -> Post:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if target.school_id != actor.school_id and not actor.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé à cet établissement")
    if not actor.is_superadmin:
        spec = ROLE_PROFILES.get(profile_code)
        if not spec:
            raise HTTPException(status_code=404, detail="Profil RBAC inconnu")
        non_delegable = [code for code in spec["permissions"] if not user_can_grant_permission(db, actor, code)]
        if non_delegable:
            raise HTTPException(status_code=403, detail=f"Profil non délégable à ce niveau: {', '.join(non_delegable)}")
    post = ensure_profile(db, target.school_id, profile_code)
    existing = db.query(UserPost).filter_by(user_id=target.id, post_id=post.id).first()
    if existing is None:
        db.add(UserPost(user_id=target.id, post_id=post.id)); db.commit()
    return post
