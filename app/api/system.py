from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.paths import data_dir
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.services.backup import (backup_root, create_backup, list_backups, prepare_restore, get_restore_state, cancel_restore)
from app.services.cloud_backup_providers import sync_backup_to_cloud_destinations
from app.services.upgrade import get_upgrade_status, prepare_upgrade, cancel_upgrade
from app.services.production import production_health, readiness, security_posture
from app.services.capacity import capacity_snapshot
from app.services.operations import system_overview, prepare_release_manifest

router = APIRouter(prefix="/api/system", tags=["Système"])


@router.get("/health", dependencies=[Depends(require_permission("administration.system.view"))])
def health_detail(current_user: User = Depends(get_current_user)):
    return {"health": production_health(None)}


@router.get("/capacity", dependencies=[Depends(require_permission("administration.system.view"))])
def capacity_detail(current_user: User = Depends(get_current_user)):
    """Diagnostic capacité: latence, erreurs et état du pool SQL."""
    return capacity_snapshot()


@router.get("/security-posture", dependencies=[Depends(require_permission("administration.system.view"))])
def security_posture_detail(current_user: User = Depends(get_current_user)):
    return security_posture()


@router.get("/status", dependencies=[Depends(require_permission("administration.system.view"))])
def status(current_user: User = Depends(get_current_user)):
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "data_dir": str(data_dir()),
        "database": settings.DATABASE_URL.split(":///")[-1] if settings.DATABASE_URL.startswith("sqlite") else "external",
        "backup_count": len(list_backups()),
        "status": "ready",
    }


@router.post("/backup", dependencies=[Depends(require_permission("administration.backup.create"))])
def backup(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        path = create_backup()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sauvegarde impossible: {exc}") from exc
    # La sauvegarde locale (garantie principale) est déjà acquise à ce stade
    # quoi qu'il arrive ensuite. L'envoi cloud est une couche supplémentaire
    # optionnelle : son échec ne doit jamais transformer une sauvegarde
    # locale réussie en réponse d'erreur pour l'utilisateur.
    cloud_results = sync_backup_to_cloud_destinations(db, path)
    return {"status": "ok", "name": path.name, "size": path.stat().st_size, "cloud": cloud_results}


@router.get("/backups", dependencies=[Depends(require_permission("administration.backup.view"))])
def backups(current_user: User = Depends(get_current_user)):
    return {"items": list_backups()}


@router.get("/backups/{name}/download", dependencies=[Depends(require_permission("administration.backup.view"))])
def download_backup(name: str, current_user: User = Depends(get_current_user)):
    safe = Path(name).name
    path = backup_root() / safe
    if path != backup_root() / name or not path.exists() or path.suffix.lower() != ".zip":
        raise HTTPException(status_code=404, detail="Sauvegarde introuvable")
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.get("/restore/status", dependencies=[Depends(require_permission("administration.restore.view"))])
def restore_status(current_user: User = Depends(get_current_user)):
    return {"pending": get_restore_state()}


@router.post("/restore/prepare", dependencies=[Depends(require_permission("administration.restore.execute"))])
async def restore_prepare(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not file.filename or Path(file.filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="Une archive ZIP SIGMA est requise")
    staging = backup_root() / ".restore_upload.tmp.zip"
    max_bytes = settings.RESTORE_MAX_UPLOAD_BYTES
    try:
        written = 0
        with staging.open("wb") as dst:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="Archive de restauration trop volumineuse")
                dst.write(chunk)
        try:
            plan = prepare_restore(staging)
        except (ValueError, RuntimeError, OSError) as exc:
            raise HTTPException(status_code=400, detail=f"Restauration refusée: {exc}") from exc
        return {"status": "pending_restart", "plan": plan, "message": "La restauration est préparée. Redémarrez SIGMA pour l'appliquer."}
    finally:
        staging.unlink(missing_ok=True)


@router.post("/restore/cancel", dependencies=[Depends(require_permission("administration.restore.execute"))])
def restore_cancel(current_user: User = Depends(get_current_user)):
    return cancel_restore()


@router.get("/upgrade/status", dependencies=[Depends(require_permission("administration.upgrade.view"))])
def upgrade_status(current_user: User = Depends(get_current_user)):
    try:
        return get_upgrade_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"État de mise à niveau indisponible: {exc}") from exc


@router.post("/upgrade/prepare", dependencies=[Depends(require_permission("administration.upgrade.execute"))])
def upgrade_prepare(current_user: User = Depends(get_current_user)):
    try:
        return prepare_upgrade()
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Mise à niveau refusée: {exc}") from exc


@router.post("/upgrade/cancel", dependencies=[Depends(require_permission("administration.upgrade.execute"))])
def upgrade_cancel(current_user: User = Depends(get_current_user)):
    return cancel_upgrade()


@router.get("/operations", dependencies=[Depends(require_permission("administration.operations.view"))])
def operations_overview(current_user: User = Depends(get_current_user)):
    return system_overview()


@router.post("/backups/prune", dependencies=[Depends(require_permission("administration.operations.execute"))])
def backups_prune(current_user: User = Depends(get_current_user)):
    from app.services.backup import prune_backups
    return prune_backups()


@router.post("/release/validate", dependencies=[Depends(require_permission("administration.operations.execute"))])
async def release_validate(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not file.filename or Path(file.filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="Un package ZIP SIGMA est requis")
    staging = backup_root() / ".release_validate.tmp.zip"
    try:
        max_bytes = settings.RESTORE_MAX_UPLOAD_BYTES
        written = 0
        with staging.open("wb") as dst:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="Package de validation trop volumineux")
                dst.write(chunk)
        try:
            return prepare_release_manifest(staging)
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=f"Package refusé: {exc}") from exc
    finally:
        staging.unlink(missing_ok=True)
