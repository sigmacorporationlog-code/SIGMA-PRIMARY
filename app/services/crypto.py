"""Chiffrement au repos pour les secrets applicatifs (jetons OAuth des
destinations cloud de sauvegarde, etc.).

On dérive une clé Fernet (AES-128 en mode CBC + HMAC, via `cryptography`)
à partir de SECRET_KEY plutôt que de générer/stocker une clé séparée :
SECRET_KEY est déjà le secret racine protégé de l'installation (utilisé
pour signer les JWT), et ajouter une deuxième clé à gérer/sauvegarder
séparément serait une source d'erreur opérationnelle de plus (perdre cette
clé rendrait les jetons stockés illisibles pour toujours).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    # Fernet exige une clé de 32 octets encodée en base64 urlsafe. On dérive
    # cette clé de SECRET_KEY via SHA-256 (peu importe la longueur ou le
    # format de SECRET_KEY en entrée, la sortie est toujours conforme).
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    """Chiffre une chaîne (jeton d'accès, jeton de rafraîchissement...)."""
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Déchiffre une valeur produite par encrypt_secret.

    Lève ValueError (pas InvalidToken directement) si le jeton est corrompu
    ou si SECRET_KEY a changé depuis le chiffrement — pour que les appelants
    n'aient qu'un seul type d'exception à intercepter, quelle qu'en soit la
    cause exacte.
    """
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Secret illisible : jeton corrompu ou SECRET_KEY a changé") from exc
