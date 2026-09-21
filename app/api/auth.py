from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, hash_password, validate_password, create_access_token, create_refresh_token, decode_token
from app.core.config import scrub_initial_admin_password
from app.deps import get_current_user, get_current_user_for_auth
from app.models.security import User, PasswordResetToken
from app.schemas.security import TokenResponse, UserOut, PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm
from app.services.audit import log_action
from app.services.email import smtp_configured, send_password_reset_email
from app.services.rate_limit import RateLimitExceeded, limiter

_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()




def _refresh_cookie_secure() -> bool:
    """Décide si le cookie de refresh doit porter l'attribut Secure.

    En production réseau/HTTPS, Secure reste activé par défaut. Le déploiement
    LAN Windows (BIND_HOST=0.0.0.0, HTTP sans certificat) définit explicitement
    AUTH_COOKIE_SECURE=false, sans quoi aucun navigateur n'enverrait jamais le
    cookie et personne ne resterait connecté.
    """
    if settings.AUTH_COOKIE_SECURE is not None:
        return settings.AUTH_COOKIE_SECURE
    return settings.ENV.lower() == "production"

def _issue_tokens(user: User) -> TokenResponse:
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"school_id": user.school_id, "token_version": user.token_version},
    )
    refresh_token = create_refresh_token(subject=str(user.id), token_version=user.token_version)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, must_change_password=user.must_change_password)


@router.post("/login", response_model=TokenResponse)
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_key = request.client.host if request.client else "unknown"
    username_key = form_data.username.strip().lower()[:160]
    try:
        limiter.check(
            f"login:ip:{client_key}",
            limit=settings.LOGIN_RATE_LIMIT,
            window_seconds=settings.LOGIN_RATE_WINDOW_SECONDS,
        )
        limiter.check(
            f"login:user:{username_key}",
            limit=settings.LOGIN_RATE_LIMIT,
            window_seconds=settings.LOGIN_RATE_WINDOW_SECONDS,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(429, "Trop de tentatives de connexion. Réessayez plus tard.", headers={"Retry-After": str(settings.LOGIN_RATE_WINDOW_SECONDS)}) from exc

    user = db.query(User).filter(User.username == form_data.username).first()
    invalid_credentials = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiant ou mot de passe incorrect")
    if user is None:
        # Même coût cryptographique qu'un compte existant pour réduire l'énumération
        # par différence de temps de réponse.
        verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
        raise invalid_credentials
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise invalid_credentials
    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    # Modernise silencieusement les anciens hashes bcrypt au format sécurisé V4.46.
    if not user.hashed_password.startswith("$sigma$bcrypt$sha256$"):
        user.hashed_password = hash_password(form_data.password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    tokens = _issue_tokens(user)
    if response is not None:
        response.set_cookie(
        "sigma_refresh",
        tokens.refresh_token,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/api/auth",
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(db: Session = Depends(get_db), response: Response = None, sigma_refresh: str | None = Cookie(default=None)):
    refresh_token = sigma_refresh

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide")
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    if int(payload.get("token_version", 0)) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token révoqué")
    tokens = _issue_tokens(user)
    response.set_cookie(
        "sigma_refresh",
        tokens.refresh_token,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            path="/api/auth",
        )
    return tokens


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    response.delete_cookie("sigma_refresh", path="/api/auth")
    return {"status": "ok", "message": "Session révoquée"}


@router.post("/change-password")
def change_password(payload: PasswordChangeRequest, current_user: User = Depends(get_current_user_for_auth), db: Session = Depends(get_db)):
    try:
        validate_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "Le nouveau mot de passe doit être différent")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False
    current_user.token_version += 1
    scrub_initial_admin_password()
    # Sur une installation Windows neuve, supprimer le mémo contenant le mot de passe
    # initial dès que celui-ci a effectivement été remplacé.
    try:
        from app.core.paths import data_dir
        (data_dir() / "first-run-credentials.txt").unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Impossible de supprimer le fichier first-run-credentials.txt: %s", exc)
    db.commit()
    log_action(db, current_user.school_id, current_user, "user.password.change", "User", current_user.id)
    return {"status": "ok", "message": "Mot de passe modifié. Reconnectez-vous avec votre nouveau mot de passe."}


@router.post("/forgot-password", status_code=202)
def forgot_password(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    # Le message HTTP est identique quel que soit le compte pour empêcher l'énumération.
    reset_ip = request.client.host if request.client else "unknown"
    reset_identifier = payload.identifier.strip().lower()[:160]
    try:
        limiter.check(
            f"password-reset:ip:{reset_ip}",
            limit=settings.PASSWORD_RESET_RATE_LIMIT * 3,
            window_seconds=settings.PASSWORD_RESET_RATE_WINDOW_SECONDS,
        )
        limiter.check(
            f"password-reset:identity:{reset_identifier}",
            limit=settings.PASSWORD_RESET_RATE_LIMIT,
            window_seconds=settings.PASSWORD_RESET_RATE_WINDOW_SECONDS,
        )
    except RateLimitExceeded:
        return {"status": "accepted", "message": "Si un compte correspond, un message de récupération sera envoyé."}

    identifier = payload.identifier.strip()
    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
    if user and user.is_active and user.email and smtp_configured():
        raw = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        # Un seul jeton actif par utilisateur.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).delete(synchronize_session=False)
        row = PasswordResetToken(
            user_id=user.id,
            token_hash=_token_hash(raw),
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
            created_at=now,
            request_ip=request.client.host if request.client else None,
        )
        db.add(row)
        db.commit()
        reset_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/dashboard/reset-password.html?token={raw}"
        try:
            send_password_reset_email(user.email, reset_url, user.first_name)
        except Exception as exc:
            # Ne révèle jamais à l'appelant qu'un compte existe; on invalide le jeton si le transport échoue.
            logger.exception("Échec d'envoi du message de récupération pour l'utilisateur %s", user.id)
            db.delete(row)
            db.commit()
    return {"status": "accepted", "message": "Si un compte correspond, un message de récupération sera envoyé."}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        validate_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _token_hash(payload.token)).first()
    now = datetime.now(timezone.utc)
    if not row or row.used_at is not None or row.expires_at <= now:
        raise HTTPException(400, "Jeton de récupération invalide ou expiré")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Jeton de récupération invalide")
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    user.token_version += 1
    row.used_at = now
    scrub_initial_admin_password()
    db.commit()
    log_action(db, user.school_id, None, "user.password.reset", "User", user.id, new_value="self-service")
    return {"status": "ok", "message": "Mot de passe réinitialisé. Vous pouvez maintenant vous connecter."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user_for_auth)):
    return current_user
