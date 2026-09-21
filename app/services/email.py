"""Minimal SMTP transport used for security-critical account recovery."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def send_password_reset_email(to_email: str, reset_url: str, first_name: str = "") -> None:
    if not smtp_configured():
        raise RuntimeError("SMTP non configuré")
    msg = EmailMessage()
    msg["Subject"] = "SIGMA — Réinitialisation de votre mot de passe"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    greeting = f"Bonjour {first_name}," if first_name else "Bonjour,"
    msg.set_content(
        f"{greeting}\n\n"
        "Une demande de réinitialisation du mot de passe de votre compte SIGMA a été effectuée.\n\n"
        f"Utilisez ce lien dans les {settings.PASSWORD_RESET_EXPIRE_MINUTES} prochaines minutes :\n{reset_url}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
        "SIGMA"
    )
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
