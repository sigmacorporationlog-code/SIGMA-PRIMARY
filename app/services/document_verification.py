"""Jetons signés pour vérifier publiquement l'authenticité des documents SIGMA."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

DOCUMENT_TOKEN_TYPE = "sigma_document_verification"
DOCUMENT_TOKEN_DAYS = 3650


def create_document_token(document_type: str, document_id: int, school_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(document_id),
        "school_id": school_id,
        "document_type": document_type,
        "type": DOCUMENT_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(days=DOCUMENT_TOKEN_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_document_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != DOCUMENT_TOKEN_TYPE:
        return None
    if payload.get("document_type") not in {"bulletin", "receipt"}:
        return None
    if not str(payload.get("sub", "")).isdigit() or not str(payload.get("school_id", "")).isdigit():
        return None
    return payload
