from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, validate_password
from app.deps import get_current_user, require_permission, assert_school_access
from app.models.security import User, Post, Permission, PostPermission, UserPost, Delegation
from app.schemas.security import (
    UserCreate, UserOut, PostCreate, PostOut, PostPermissionAssign, PostPermissionBulkAssign, UserPostAssign, DelegationCreate, AdminPasswordReset,
)
from app.services.audit import log_action
from app.services.cloud import enforce_subscription_capacity, SubscriptionError
from app.services.authorization import user_can_grant_permission

router = APIRouter(prefix="/api", tags=["Administration"])


# ---------- Utilisateurs ----------

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.users.create"))])
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, payload.school_id)
    try:
        enforce_subscription_capacity(db, payload.school_id, "users")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Cet identifiant existe déjà")

    user = User(
        school_id=payload.school_id,
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, payload.school_id, current_user, "user.create", "User", user.id, new_value=payload.username)
    return user


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_permission("administration.users.view"))])
def list_users(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, school_id)
    return db.query(User).filter(User.school_id == school_id).all()


@router.get("/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_permission("administration.users.view"))])
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    assert_school_access(current_user, user.school_id)
    return user


@router.post("/users/{user_id}/password-reset", dependencies=[Depends(require_permission("administration.users.modify"))])
def admin_reset_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superadmin:
        from app.services.authorization import user_has_permission
        if not user_has_permission(db, current_user, "administration.users.modify"):
            raise HTTPException(status_code=403, detail="Permission requise: administration.users.modify")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    assert_school_access(current_user, target.school_id)
    try:
        validate_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    target.hashed_password = hash_password(payload.new_password)
    target.must_change_password = payload.force_change
    target.token_version += 1
    target.failed_login_attempts = 0
    target.locked_until = None
    db.commit()
    log_action(
        db, target.school_id, current_user, "user.password.admin_reset", "User", target.id,
        new_value=f"force_change={payload.force_change}",
    )
    return {"status": "ok", "user_id": target.id, "must_change_password": target.must_change_password}


# ---------- Postes (rôles configurables) ----------

@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.posts.create"))])
def create_post(payload: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, payload.school_id)
    post = Post(school_id=payload.school_id, name=payload.name, description=payload.description)
    db.add(post)
    db.commit()
    db.refresh(post)
    log_action(db, payload.school_id, current_user, "post.create", "Post", post.id, new_value=payload.name)
    return post


@router.get("/posts", response_model=list[PostOut], dependencies=[Depends(require_permission("administration.posts.view"))])
def list_posts(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, school_id)
    return db.query(Post).filter(Post.school_id == school_id).all()


@router.post("/posts/{post_id}/permissions", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.permissions.modify"))])
def assign_permission_to_post(
    post_id: int, payload: PostPermissionAssign, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    assert_school_access(current_user, post.school_id)
    permission = db.query(Permission).filter(Permission.code == payload.permission_code).first()
    if permission is None:
        raise HTTPException(status_code=404, detail=f"Permission inconnue: {payload.permission_code}")
    if not user_can_grant_permission(db, current_user, payload.permission_code):
        raise HTTPException(status_code=403, detail="Un administrateur ne peut transmettre que les permissions qu'il détient directement à portée établissement")

    link = PostPermission(post_id=post.id, permission_id=permission.id, scope=payload.scope)
    db.add(link)
    db.commit()
    log_action(
        db, post.school_id, current_user, "post.permission.assign", "PostPermission", post.id,
        new_value=f"{payload.permission_code} scope={payload.scope}",
    )
    return {"status": "ok"}


@router.post("/posts/{post_id}/permissions/bulk", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.permissions.modify"))])
def assign_permissions_to_post_bulk(
    post_id: int, payload: PostPermissionBulkAssign, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Coche multiple à la création/édition d'un poste : applique plusieurs
    permissions en un seul appel plutôt que d'enchaîner N requêtes. Chaque
    code suit la même règle de non-délégation excessive que l'attribution
    unitaire ; un seul code refusé fait échouer tout l'appel (aucune
    permission n'est accordée à moitié), pour que l'écran reflète fidèlement
    ce qui a réellement été enregistré.
    """
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    assert_school_access(current_user, post.school_id)

    permissions = {
        p.code: p
        for p in db.query(Permission).filter(Permission.code.in_(payload.permission_codes)).all()
    }
    unknown = [code for code in payload.permission_codes if code not in permissions]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Permissions inconnues: {', '.join(unknown)}")
    non_delegable = [code for code in payload.permission_codes if not user_can_grant_permission(db, current_user, code)]
    if non_delegable:
        raise HTTPException(
            status_code=403,
            detail=f"Un administrateur ne peut transmettre que les permissions qu'il détient directement à portée établissement: {', '.join(non_delegable)}",
        )

    already_assigned = {
        pp.permission_id
        for pp in db.query(PostPermission).filter(
            PostPermission.post_id == post.id, PostPermission.scope == payload.scope
        ).all()
    }
    added = []
    for code in payload.permission_codes:
        permission = permissions[code]
        if permission.id in already_assigned:
            continue
        db.add(PostPermission(post_id=post.id, permission_id=permission.id, scope=payload.scope))
        added.append(code)
    db.commit()
    if added:
        log_action(
            db, post.school_id, current_user, "post.permission.assign_bulk", "PostPermission", post.id,
            new_value=f"{added} scope={payload.scope}",
        )
    return {"status": "ok", "added": added, "already_present": [c for c in payload.permission_codes if c not in added]}


@router.get("/posts/{post_id}/permissions", dependencies=[Depends(require_permission("administration.permissions.view"))])
def list_post_permissions(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Poste introuvable")
    assert_school_access(current_user, post.school_id)
    links = db.query(PostPermission).filter(PostPermission.post_id == post_id).all()
    return [
        {"id": link.id, "permission_code": link.permission.code, "label": link.permission.label, "scope": link.scope}
        for link in links
    ]


@router.delete("/posts/{post_id}/permissions/{link_id}",
                dependencies=[Depends(require_permission("administration.permissions.modify"))])
def remove_post_permission(post_id: int, link_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    link = db.get(PostPermission, link_id)
    post = db.get(Post, post_id)
    if link is None or post is None or link.post_id != post_id:
        raise HTTPException(status_code=404, detail="Attribution de permission introuvable")
    assert_school_access(current_user, post.school_id)
    db.delete(link)
    db.commit()
    return {"status": "ok"}


@router.get("/users/{user_id}/posts", dependencies=[Depends(require_permission("administration.users.view"))])
def list_user_posts(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    assert_school_access(current_user, user.school_id)
    links = db.query(UserPost).filter(UserPost.user_id == user_id).all()
    return [{"id": link.id, "post_id": link.post_id, "post_name": link.post.name} for link in links]


@router.post("/user-posts", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.users.modify"))])
def assign_user_to_post(payload: UserPostAssign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, payload.user_id)
    post = db.get(Post, payload.post_id)
    if user is None or post is None:
        raise HTTPException(status_code=404, detail="Utilisateur ou poste introuvable")
    if user.school_id != post.school_id:
        raise HTTPException(status_code=400, detail="Utilisateur et poste doivent appartenir au même établissement")
    assert_school_access(current_user, user.school_id)
    if not current_user.is_superadmin:
        for pp in db.query(PostPermission).filter(PostPermission.post_id == post.id).all():
            if not user_can_grant_permission(db, current_user, pp.permission.code):
                raise HTTPException(status_code=403, detail=f"Le poste contient une permission non délégable: {pp.permission.code}")

    link = UserPost(user_id=user.id, post_id=post.id)
    db.add(link)
    db.commit()
    log_action(db, user.school_id, current_user, "user.post.assign", "UserPost", user.id, new_value=post.name)
    return {"status": "ok"}


# ---------- Délégations temporaires ----------

@router.post("/delegations", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.permissions.modify"))])
def create_delegation(payload: DelegationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, payload.school_id)
    granted_by = db.get(User, payload.granted_by_id)
    granted_to = db.get(User, payload.granted_to_id)
    if not granted_by or not granted_to or granted_by.school_id != payload.school_id or granted_to.school_id != payload.school_id:
        raise HTTPException(status_code=400, detail="Les utilisateurs de la délégation doivent appartenir à l'établissement")
    if not current_user.is_superadmin and granted_by.id != current_user.id:
        raise HTTPException(status_code=403, detail="Une délégation doit être émise par l'utilisateur connecté")
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=400, detail="La date de début doit précéder ou égaler la date de fin")
    permission = db.query(Permission).filter(Permission.code == payload.permission_code).first()
    if permission is None:
        raise HTTPException(status_code=404, detail=f"Permission inconnue: {payload.permission_code}")
    if not user_can_grant_permission(db, current_user, payload.permission_code):
        raise HTTPException(status_code=403, detail="Une délégation ne peut transmettre qu'une permission détenue directement à portée établissement")

    delegation = Delegation(
        school_id=payload.school_id,
        granted_by_id=payload.granted_by_id,
        granted_to_id=payload.granted_to_id,
        permission_id=permission.id,
        scope=payload.scope,
        start_date=date_type.fromisoformat(payload.start_date),
        end_date=date_type.fromisoformat(payload.end_date),
        reason=payload.reason,
    )
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    log_action(
        db, payload.school_id, current_user, "delegation.create", "Delegation", delegation.id,
        new_value=f"{payload.permission_code} -> user {payload.granted_to_id} du {payload.start_date} au {payload.end_date}",
    )
    return {"status": "ok", "delegation_id": delegation.id}


# ---------- Journal d'audit (lecture seule, non modifiable) ----------

@router.get("/permissions", dependencies=[Depends(require_permission("administration.permissions.view"))])
def list_permissions(module: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Catalogue des permissions atomiques disponibles (pour alimenter le
    formulaire d'attribution de permissions à un poste dans l'interface)."""
    query = db.query(Permission)
    if module:
        query = query.filter(Permission.module == module)
    permissions = query.order_by(Permission.module, Permission.code).all()
    return [{"code": p.code, "module": p.module, "label": p.label} for p in permissions]


@router.get("/audit-logs", dependencies=[Depends(require_permission("administration.audit.view"))])
def list_audit_logs(school_id: int, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.security import AuditLog
    assert_school_access(current_user, school_id)
    limit = min(max(limit, 1), 500)

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.school_id == school_id)
        .order_by(AuditLog.at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id, "at": log.at, "user_id": log.user_id, "action": log.action,
            "entity_type": log.entity_type, "entity_id": log.entity_id,
            "old_value": log.old_value, "new_value": log.new_value,
        }
        for log in logs
    ]

# ---------- RBAC Enterprise : profils standardisés ----------

@router.get("/rbac/profiles", dependencies=[Depends(require_permission("administration.permissions.view"))])
def rbac_profiles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Catalogue des profils de postes standard SIGMA, sans attribution implicite."""
    from app.services.rbac_enterprise import profile_catalog
    return profile_catalog()


@router.post("/rbac/users/{user_id}/profile", dependencies=[Depends(require_permission("administration.users.modify"))])
def assign_rbac_profile(
    user_id: int, profile_code: str,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    from app.services.rbac_enterprise import assign_profile
    # Un acteur doit disposer de la permission d'administration des utilisateurs,
    # sauf superadmin. Cela évite qu'un simple utilisateur s'élève lui-même.
    if not current_user.is_superadmin:
        from app.services.authorization import user_has_permission
        if not user_has_permission(db, current_user, "administration.users.modify"):
            raise HTTPException(status_code=403, detail="Permission requise: administration.users.modify")
    post = assign_profile(db, current_user, user_id, profile_code)
    log_action(db, current_user.school_id, current_user, "rbac.profile.assign", "UserPost", user_id,
               new_value=f"profile={profile_code};post={post.id}")
    return {"status": "ok", "user_id": user_id, "profile": profile_code, "post_id": post.id, "post_name": post.name}
