"""Supervision et exploitation V4.4 de SIGMA."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import shutil

from app.core.config import settings
from app.core.paths import data_dir
from app.core.database import is_sqlite
from app.services.backup import list_backups, prune_backups
from app.services.production import backup_check
from app.services.upgrade import get_upgrade_status


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def system_overview() -> dict:
    root = data_dir()
    usage = shutil.disk_usage(root)
    upgrade = get_upgrade_status()
    backups = backup_check()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "application": {"name": settings.APP_NAME, "version": settings.V3_VERSION, "environment": settings.ENV},
        "runtime": {"platform": platform.platform(), "python": platform.python_version(), "database": "sqlite" if is_sqlite else "external"},
        "storage": {"path": str(root), "free_bytes": usage.free, "total_bytes": usage.total},
        "backups": backups,
        "upgrade": upgrade,
    }


def prepare_release_manifest(package: Path) -> dict:
    """Analyse un package SIGMA avant installation sans exécuter son contenu."""
    package = Path(package)
    if not package.exists() or not package.is_file():
        raise ValueError("Package introuvable")
    if package.suffix.lower() != ".zip":
        raise ValueError("Le package doit être un ZIP")
    import zipfile
    with zipfile.ZipFile(package) as zf:
        if zf.testzip() is not None:
            raise ValueError("Package ZIP corrompu")
        names = set(zf.namelist())
        if not any(name.endswith("app/main.py") for name in names):
            raise ValueError("Package SIGMA non reconnu")
        manifest = None
        for name in ("release.json", "docs/release.json"):
            if name in names:
                manifest = json.loads(zf.read(name).decode("utf-8"))
                break
    return {"status": "validated", "filename": package.name, "size": package.stat().st_size, "sha256": _sha256(package), "manifest": manifest}
