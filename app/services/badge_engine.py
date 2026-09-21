"""Moteur métier SIGMA BADGE 3.5.

QR codes contain only an opaque access token. No personal information is
encoded in the QR payload itself.
"""
from datetime import date
from app.services.card_engine import generate_access_code

VALID_STATUSES = {"active", "printed", "delivered", "lost", "damaged", "revoked", "replaced"}
STRATEGIES = {"sequential", "year_sequence", "year_level_sequence", "alphanumeric"}


def next_card_number(db, school_id: int, strategy: str = "year_sequence", level_code: str | None = None) -> str:
    from sqlalchemy import update
    from app.models.organization import School
    school = db.get(School, school_id)
    if not school:
        raise ValueError("Établissement introuvable")
    result = db.execute(update(School).where(School.id == school_id).values(badge_next_sequence=School.badge_next_sequence + 1))
    if result.rowcount != 1:
        raise ValueError("Impossible d'incrémenter la séquence des cartes")
    db.refresh(school)
    count = school.badge_next_sequence
    year = date.today().year
    if strategy == "sequential":
        return f"CARD-{count:06d}"
    if strategy == "year_level_sequence" and level_code:
        return f"{year}-{level_code.upper()[:8]}-{count:04d}"
    if strategy == "alphanumeric":
        return f"SIGMA-{year}-{count:06X}"
    return f"CARD-{year}-{count:06d}"


def secure_qr_payload(access_code: str) -> str:
    return f"SIGMA-BADGE:{access_code}"


def normalize_status(status: str) -> str:
    status = status.strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Statut de badge invalide: {status}")
    return status
