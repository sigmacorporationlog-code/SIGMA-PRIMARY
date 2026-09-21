"""Diagnostic and production-readiness helpers for SIGMA 3.9.

The functions here are deliberately dependency-light so they work in the
Windows standalone build as well as on a Linux server.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, is_sqlite
from app.core.paths import data_dir
from app.services.backup import list_backups


def migration_check() -> dict:
    """Vérifie que la base correspond exactement à la révision Alembic de l'application."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        head = ScriptDirectory.from_config(cfg).get_current_head()
        with engine.connect() as conn:
            if is_sqlite:
                current = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
            else:
                current = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
        if current == head:
            return {"status": "ok", "current": current, "head": head}
        return {"status": "error", "current": current, "head": head, "error": "Schéma non aligné avec la révision applicative"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def database_check() -> dict:
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        return {"status": "error", "latency_ms": round((time.perf_counter() - started) * 1000, 2), "error": str(exc)[:300]}


def storage_check() -> dict:
    root = data_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(root)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        return {
            "status": "ok" if free_gb >= 1 else "warning",
            "path": str(root),
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300]}


def backup_check() -> dict:
    items = list_backups()
    valid = [x for x in items if x.get("valid")]
    latest = valid[0] if valid else None
    age_hours = None
    if latest:
        try:
            created = datetime.fromisoformat(str(latest["created_at"]).replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = round((_utc_now() - created).total_seconds() / 3600, 2)
        except Exception:
            age_hours = None
    if not latest:
        status = "critical"
    elif age_hours is not None and age_hours > 48:
        status = "warning"
    else:
        status = "ok"
    return {"status": status, "count": len(items), "valid_count": len(valid), "latest": latest, "latest_age_hours": age_hours}


def readiness(db: Session) -> dict:
    db_state = database_check()
    storage = storage_check()
    from app.services.observability import snapshot as observability_snapshot
    metrics = observability_snapshot()
    migration = migration_check()
    checks = {"database": db_state, "storage": storage, "migration": migration}
    ok = db_state["status"] == "ok" and storage["status"] in {"ok", "warning"} and migration["status"] == "ok"
    return {"status": "ready" if ok else "not_ready", "checks": checks, "observability": metrics}


def production_health(db: Session) -> dict:
    db_state = database_check()
    storage = storage_check()
    backups = backup_check()
    from app.services.observability import snapshot as observability_snapshot
    metrics = observability_snapshot()
    migration = migration_check()
    checks = {"database": db_state, "storage": storage, "migration": migration, "backups": backups}
    critical = any(v.get("status") == "error" or v.get("status") == "critical" for v in checks.values())
    warning = any(v.get("status") == "warning" for v in checks.values())
    status = "critical" if critical else ("warning" if warning else "ok")
    return {
        "status": status,
        "timestamp": _utc_now().isoformat(),
        "version": settings.V3_VERSION,
        "environment": settings.ENV,
        "database_engine": "sqlite" if is_sqlite else "external",
        "checks": checks,
        "observability": metrics,
    }


def security_posture() -> dict:
    warnings: list[str] = []
    if not settings.SECRET_KEY:
        warnings.append("SECRET_KEY non définie")
    if settings.ENV.lower() == "production" and settings.OPEN_BROWSER:
        warnings.append("OPEN_BROWSER devrait être désactivé en production")
    if settings.ENV.lower() == "production" and is_sqlite:
        warnings.append("SQLite est déconseillé pour un déploiement Cloud multi-utilisateur")

    # Les documents contractuels livrés avec le produit sont des modèles.
    # Tant que des marqueurs éditoriaux restent présents, l'installation ne
    # doit pas être présentée comme juridiquement finalisée.
    try:
        from app.legal.documents import LEGAL_DOCUMENTS
        placeholder_markers = ("[ÉDITEUR SIGMA]", "[RAISON SOCIALE]", "[COMPLÉTER", "[DÉCRIRE ICI", "[NOM OU SERVICE]")
        pending = [doc["code"] for doc in LEGAL_DOCUMENTS if any(marker in doc["content"] for marker in placeholder_markers)]
        if pending:
            warnings.append("Documents juridiques à finaliser : " + ", ".join(pending))
    except Exception:
        warnings.append("Vérification des documents juridiques indisponible")

    return {"status": "warning" if warnings else "ok", "warnings": warnings}
