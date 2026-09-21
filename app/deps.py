from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.security import User
from app.services.authorization import user_has_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user_for_auth(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    try:
        if int(payload.get("token_version", 0)) != user.token_version:
            raise credentials_exception
    except (TypeError, ValueError):
        raise credentials_exception
    return user



def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user = get_current_user_for_auth(token=token, db=db)
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="PASSWORD_CHANGE_REQUIRED")
    return user

def require_permission(permission_code: str, context_builder=None):
    """
    Fabrique de dépendance FastAPI pour protéger un endpoint avec une
    permission donnée. `context_builder` reçoit les path/query params déjà
    résolus par FastAPI et retourne le contexte de scope à vérifier.

    Usage:
        @router.post("/grades", dependencies=[Depends(require_permission("academic.grades.create"))])
    """

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        context = {}
        if context_builder:
            # Les paramètres de route sont déjà résolus dans request.path_params.
            # On transmet aussi query_params, l'utilisateur et la session afin
            # que les permissions à périmètre puissent être évaluées sans
            # contourner FastAPI avec des dépendances globales.
            try:
                context = context_builder(
                    path_params=dict(request.path_params),
                    query_params=dict(request.query_params),
                    current_user=current_user,
                    db=db,
                ) or {}
            except TypeError:
                # Compatibilité avec un ancien builder sans arguments.
                context = context_builder() or {}
        if not user_has_permission(db, current_user, permission_code, context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé: permission requise '{permission_code}'",
            )
        return current_user

    return dependency


def assert_school_access(current_user: User, school_id: int) -> None:
    """Garantit l'isolation multi-tenant pour toute ressource rattachée à un établissement."""
    if not current_user.is_superadmin and current_user.school_id != school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé à cet établissement")
