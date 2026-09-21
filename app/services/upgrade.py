"""Moteur de mise à niveau SIGMA sécurisé.

Une mise à niveau est préparée avec une sauvegarde de sécurité puis exécutée
au prochain démarrage, avant que l'application n'accepte des requêtes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import tempfile
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import settings
from app.core.database import engine, is_sqlite
from app.core.paths import bundle_dir, data_dir
from app.services.backup import create_backup, validate_backup, restore_backup_to_directory

UPGRADE_STATE_FILE = "upgrade_pending.json"


def upgrade_state_path() -> Path:
    return data_dir() / UPGRADE_STATE_FILE


def _alembic_config() -> Config:
    cfg = Config(str(bundle_dir() / "alembic.ini"))
    # alembic.ini déclare « script_location = alembic », un chemin RELATIF au
    # répertoire courant. Or un service Windows démarre avec C:\Windows\System32
    # comme répertoire courant : le dossier de migrations serait introuvable et
    # toute vérification de version échouerait. On l'ancre donc explicitement
    # sur le dossier des ressources embarquées.
    cfg.set_main_option("script_location", str(bundle_dir() / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def current_revision() -> str | None:
    if not is_sqlite:
        return None
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return row[0] if row else None


def head_revision() -> str:
    cfg = _alembic_config()
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(cfg).get_current_head()


def get_upgrade_status() -> dict:
    pending = None
    state = upgrade_state_path()
    if state.exists():
        pending = json.loads(state.read_text(encoding="utf-8"))
    cur = current_revision()
    head = head_revision()
    return {
        "current_revision": cur,
        "head_revision": head,
        "migration_needed": cur != head,
        "pending": pending,
    }


def prepare_upgrade() -> dict:
    state = upgrade_state_path()
    if state.exists():
        raise RuntimeError("Une mise à niveau est déjà en attente")
    status = get_upgrade_status()
    if not status["migration_needed"]:
        return {"status": "up_to_date", **status}

    safety_backup = create_backup()
    token = uuid.uuid4().hex
    plan = {
        "token": token,
        "created_at": datetime.now().isoformat(),
        "from_revision": status["current_revision"],
        "to_revision": status["head_revision"],
        "safety_backup": str(safety_backup),
        "status": "pending_restart",
    }
    state.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def cancel_upgrade() -> dict:
    state = upgrade_state_path()
    if not state.exists():
        return {"status": "none"}
    plan = json.loads(state.read_text(encoding="utf-8"))
    state.unlink(missing_ok=True)
    return {"status": "cancelled", "token": plan.get("token")}


def _stamp_existing_schema_if_unversioned(cfg: Config) -> None:
    # Les installations historiques utilisaient Base.metadata.create_all().
    # On adopte leur schéma comme point de départ Alembic au lieu de rejouer
    # des migrations initiales sur des tables déjà existantes.
    if current_revision() is not None:
        return
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    command.stamp(cfg, "head")


def _restore_safety_backup(archive: Path) -> None:
    """Replace DB/media from a validated safety archive before startup."""
    validate_backup(archive)
    root = data_dir()
    with tempfile.TemporaryDirectory(prefix="sigma_upgrade_rollback_", dir=str(root.parent)) as tmp:
        staged = Path(tmp) / "restore"
        staged.mkdir()
        restore_backup_to_directory(archive, staged)
        engine.dispose()
        db_target = root / "sigma.db"
        db_source = staged / "sigma.db"
        if db_source.exists():
            os.replace(db_source, db_target)
        media_source = staged / "media"
        media_target = root / "media"
        if media_source.exists():
            old = root / f".media.failed.{uuid.uuid4().hex}"
            if media_target.exists():
                os.replace(media_target, old)
            os.replace(media_source, media_target)
            shutil.rmtree(old, ignore_errors=True)


def apply_pending_upgrade() -> dict | None:
    state = upgrade_state_path()
    if not state.exists():
        return None
    plan = json.loads(state.read_text(encoding="utf-8"))
    safety = Path(plan["safety_backup"])
    if not safety.exists():
        raise RuntimeError("Sauvegarde de sécurité de mise à niveau introuvable")

    cfg = _alembic_config()
    try:
        if current_revision() is None:
            _stamp_existing_schema_if_unversioned(cfg)
        command.upgrade(cfg, "head")
        state.unlink(missing_ok=True)
        return {"status": "upgraded", "from_revision": plan.get("from_revision"), "to_revision": head_revision()}
    except Exception as exc:
        try:
            _restore_safety_backup(safety)
            state.unlink(missing_ok=True)
        except Exception as rollback_exc:
            raise RuntimeError(f"Mise à niveau échouée et rollback impossible: {rollback_exc}") from exc
        raise RuntimeError(f"Mise à niveau échouée; rollback effectué: {exc}") from exc
