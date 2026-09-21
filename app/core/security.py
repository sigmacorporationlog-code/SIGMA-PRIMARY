from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt, JWTError

from app.core.config import settings

import hashlib
# Les anciennes versions de SIGMA tronquaient les mots de passe à 72 octets pour
# bcrypt. Cela peut rendre deux mots de passe différents équivalents. Les nouveaux
# hashes utilisent donc un pré-hachage SHA-256 du mot de passe complet avant bcrypt.
# Les hashes legacy $2... restent vérifiables afin de permettre une migration sans
# forcer tous les comptes à être réinitialisés d'un coup.
_PASSWORD_PREFIX = "$sigma$bcrypt$sha256$"
_MIN_PASSWORD_LENGTH = 15
_MAX_PASSWORD_LENGTH = 128


def validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise ValueError("Mot de passe invalide")
    length = len(password)
    if length < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe doit contenir au moins {_MIN_PASSWORD_LENGTH} caractères")
    if length > _MAX_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe ne peut pas dépasser {_MAX_PASSWORD_LENGTH} caractères")


def _password_material(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    validate_password(password)
    hashed = bcrypt.hashpw(_password_material(password), bcrypt.gensalt())
    return _PASSWORD_PREFIX + hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith(_PASSWORD_PREFIX):
            return bcrypt.checkpw(_password_material(plain_password), hashed_password[len(_PASSWORD_PREFIX):].encode("utf-8"))
        # Compatibilité avec les comptes créés avant V4.46. Ces comptes seront
        # automatiquement modernisés lors du changement de mot de passe.
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access"}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, token_version: int = 1) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh", "token_version": token_version}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
