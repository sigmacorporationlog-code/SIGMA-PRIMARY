from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.backup_cloud import CloudBackupDestination, SUPPORTED_PROVIDERS
from app.models.security import User
from app.services.crypto import encrypt_secret
from app.services.cloud_backup_providers import upload_to_provider, CloudUploadError

router = APIRouter(prefix="/api", tags=["Sauvegarde Cloud"])


class CloudDestinationCreate(BaseModel):
    school_id: int
    provider: str
    label: str
    access_token: str
    refresh_token: str | None = None
    folder_path: str = "/SIGMA"

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, v):
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Fournisseur non supporté: {v}. Attendu: {', '.join(SUPPORTED_PROVIDERS)}")
        return v


def _out(dest: CloudBackupDestination) -> dict:
    # Les jetons ne sont jamais renvoyés, même chiffrés : une fois saisis,
    # ils ne sont plus lisibles depuis l'API — seul un nouveau jeton permet
    # de les remplacer (endpoint PATCH ci-dessous).
    return {
        "id": dest.id, "school_id": dest.school_id, "provider": dest.provider, "label": dest.label,
        "folder_path": dest.folder_path, "is_active": dest.is_active,
        "last_synced_at": dest.last_synced_at.isoformat() if dest.last_synced_at else None,
        "last_sync_error": dest.last_sync_error,
    }


@router.get("/cloud-backup-destinations", dependencies=[Depends(require_permission("administration.backup.view"))])
def list_cloud_destinations(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(CloudBackupDestination).filter(CloudBackupDestination.school_id == school_id).all()
    return {"items": [_out(d) for d in items]}


@router.post("/cloud-backup-destinations", status_code=201, dependencies=[Depends(require_permission("administration.backup.create"))])
def add_cloud_destination(payload: CloudDestinationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dest = CloudBackupDestination(
        school_id=payload.school_id,
        provider=payload.provider,
        label=payload.label,
        encrypted_access_token=encrypt_secret(payload.access_token),
        encrypted_refresh_token=encrypt_secret(payload.refresh_token) if payload.refresh_token else None,
        folder_path=payload.folder_path,
        is_active=True,
    )
    db.add(dest)
    db.commit()
    db.refresh(dest)
    return _out(dest)


@router.post("/cloud-backup-destinations/{destination_id}/test", dependencies=[Depends(require_permission("administration.backup.create"))])
def test_cloud_destination(destination_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Envoie un petit fichier de test pour vérifier que le jeton fonctionne
    réellement, sans attendre la prochaine sauvegarde complète."""
    from app.services.crypto import decrypt_secret

    dest = db.get(CloudBackupDestination, destination_id)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination introuvable")
    try:
        token = decrypt_secret(dest.encrypted_access_token)
        upload_to_provider(dest.provider, token, dest.folder_path, "sigma_test_connexion.txt", b"Test de connexion SIGMA")
    except (CloudUploadError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok"}


@router.delete("/cloud-backup-destinations/{destination_id}", dependencies=[Depends(require_permission("administration.backup.create"))])
def delete_cloud_destination(destination_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dest = db.get(CloudBackupDestination, destination_id)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination introuvable")
    db.delete(dest)
    db.commit()
    return {"status": "ok"}
