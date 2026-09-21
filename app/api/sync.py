from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.sync import SyncDevice, SyncOperation, SyncEntityVersion, SyncEntityIdentity, SyncDeliveryAck
from app.services.sync import decide_apply, apply_business_mutation, validate_operation_type, ENTITY_HANDLERS
from app.services.authorization import user_has_permission
from app.services.compatibility import compatibility
from app.core.config import settings

router = APIRouter(prefix="/api/sync", tags=["Synchronisation"])


def _update_device_sync_state(db, school_id: int, device_id: str, status: str, error: str | None = None):
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == school_id, SyncDevice.device_id == device_id
    ).first()
    if device is None:
        return
    device.last_sync_at = datetime.now(timezone.utc)
    device.last_sync_status = status
    device.last_sync_error = error
    device.status = "online" if status in {"synchronized", "pending", "conflict"} else device.status


def _is_admin(db, user) -> bool:
    return bool(user.is_superadmin or user_has_permission(db, user, "administration.settings.modify", {}))


def _device_access(db, user, device: SyncDevice, *, allow_admin: bool = True) -> bool:
    if device.school_id != user.school_id:
        return False
    if device.owner_user_id == user.id:
        return True
    if allow_admin and _is_admin(db, user):
        return True
    return False


def _operation_access(db, user, op: SyncOperation, *, allow_admin: bool = True) -> bool:
    if op.school_id != user.school_id:
        return False
    if op.user_id == user.id:
        return True
    if allow_admin and _is_admin(db, user):
        return True
    return False


def _sync_permission_allowed(db, user, entity_type: str, operation_type: str = "update", payload: dict | None = None) -> bool:
    if user.is_superadmin:
        return True
    if entity_type in {"grade", "evaluation_result"}:
        if operation_type == "create":
            code = "academic.grades.enter"
        elif operation_type == "transition":
            target = (payload or {}).get("to_state")
            code = "academic.grades.lock" if target == "locked" else "academic.report_cards.publish" if target == "published" else "academic.grades.validate"
        else:
            code = "academic.grades.modify"
    elif entity_type == "student" and operation_type == "create":
        code = "students.create"
    elif entity_type in {"student", "guardian", "student_guardian", "class_membership"}:
        code = "students.modify"
    else:
        code = "administration.settings.modify"
    return user_has_permission(db, user, code, {})



class DeviceIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    device_type: str = Field(default="client", max_length=50)
    app_version: str | None = Field(default=None, max_length=100)


class AckIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=100)
    operation_ids: list[str] = Field(min_length=1, max_length=500)


class OperationIn(BaseModel):
    operation_id: str | None = Field(default=None, min_length=8, max_length=100)
    device_id: str = Field(min_length=8, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: str = Field(min_length=1, max_length=100)
    operation_type: str = Field(pattern="^(create|update|delete|transition)$")
    base_version: int = Field(default=0, ge=0)
    payload: dict = Field(default_factory=dict)


@router.get("/compatibility")
def sync_compatibility(client_version: str, current_user: User = Depends(get_current_user)):
    result = compatibility(client_version, settings.APP_VERSION)
    return {"server_version": settings.APP_VERSION, "client_version": client_version, **result}


@router.get("/status")
def sync_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.query(SyncDevice).filter(SyncDevice.school_id == current_user.school_id).all()
    now = datetime.now(timezone.utc)
    online = sum(1 for d in devices if (now - d.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds() <= 90)
    pending = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.status == "pending",
    ).count()
    conflicts = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.status == "conflict",
    ).count()
    return {
        "status": "ok", "devices": len(devices), "online_devices": online,
        "pending": pending, "conflicts": conflicts,
        "last_sync_at": max((d.last_sync_at for d in devices if d.last_sync_at), default=None),
        "device_states": [{
            "device_id": d.device_id, "name": d.name, "status": d.status,
            "last_seen_at": d.last_seen_at, "last_sync_at": d.last_sync_at,
            "last_sync_status": d.last_sync_status, "last_sync_error": d.last_sync_error,
        } for d in devices],
    }


@router.post("/devices/register")
def register_device(data: DeviceIn, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == data.device_id
    ).first()
    if device is None:
        device = SyncDevice(school_id=current_user.school_id, owner_user_id=current_user.id, device_id=data.device_id, name=data.name)
        db.add(device)
    elif device.owner_user_id is None:
        if not _is_admin(db, current_user):
            raise HTTPException(status_code=403, detail="Appareil existant non attribué: un administrateur doit le réattribuer")
        device.owner_user_id = current_user.id
    elif not _device_access(db, current_user, device):
        raise HTTPException(status_code=403, detail="Appareil attribué à un autre compte")
    device.name = data.name
    device.device_type = data.device_type
    device.app_version = data.app_version
    device.last_seen_at = datetime.now(timezone.utc)
    device.last_ip = request.client.host if request.client else None
    device.status = "online"
    db.commit()
    db.refresh(device)
    return {"id": device.id, "device_id": device.device_id, "status": device.status, "last_seen_at": device.last_seen_at}


@router.post("/devices/heartbeat")
def heartbeat(data: DeviceIn, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == data.device_id
    ).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Appareil non enregistré")
    if not _device_access(db, current_user, device):
        raise HTTPException(status_code=403, detail="Appareil attribué à un autre compte")
    device.last_seen_at = datetime.now(timezone.utc)
    device.last_ip = request.client.host if request.client else device.last_ip
    device.app_version = data.app_version or device.app_version
    device.status = "online"
    db.commit()
    return {"status": "ok", "device_id": device.device_id, "last_seen_at": device.last_seen_at}


@router.get("/devices", dependencies=[Depends(require_permission("administration.settings.modify"))])
def devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(SyncDevice).filter(SyncDevice.school_id == current_user.school_id).order_by(SyncDevice.last_seen_at.desc()).all()
    return {"items": [
        {"device_id": d.device_id, "name": d.name, "type": d.device_type, "status": d.status,
         "last_seen_at": d.last_seen_at, "last_ip": d.last_ip, "app_version": d.app_version,
         "last_sync_at": d.last_sync_at, "last_sync_status": d.last_sync_status,
         "last_sync_error": d.last_sync_error, "owner_user_id": d.owner_user_id,
         "compatibility": compatibility(d.app_version, settings.APP_VERSION) if d.app_version else {"compatible": False, "reason": "version_unknown"}}
        for d in items
    ]}


def _canonical_version_entity_id(db, school_id: int, entity_type: str, entity_id: str) -> str:
    """Retourne l'identifiant canonique serveur pour le versionnement.

    Les créations offline utilisent un identifiant client stable. Dès que
    l'identité serveur existe, toutes les versions doivent cependant pointer
    vers l'ID serveur afin que tous les postes partagent le même compteur.
    """
    identity = db.query(SyncEntityIdentity).filter(
        SyncEntityIdentity.school_id == school_id,
        SyncEntityIdentity.entity_type == entity_type,
        SyncEntityIdentity.client_entity_id == str(entity_id),
    ).first()
    return str(identity.server_entity_id) if identity else str(entity_id)


def _pull_payload(db, operation):
    """Expose aux autres postes des références serveur quand elles existent."""
    payload = dict(operation.payload or {})
    for field, value in list(payload.items()):
        if not field.endswith("_entity_id") or value is None:
            continue
        # Le type est déduit du préfixe; student_entity_id est le cas le plus
        # fréquent pour les résultats/inscriptions.
        entity_type = field[:-len("_entity_id")]
        if entity_type not in {"student", "guardian", "class_membership", "grade", "evaluation_result"}:
            continue
        identity = db.query(SyncEntityIdentity).filter(
            SyncEntityIdentity.school_id == operation.school_id,
            SyncEntityIdentity.device_id == operation.device_id,
            SyncEntityIdentity.entity_type == entity_type,
            SyncEntityIdentity.client_entity_id == str(value),
        ).first()
        if identity is not None:
            payload[field] = identity.server_entity_id
    return payload


@router.post("/push")
def push(operations: list[OperationIn], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    for item in operations:
        try:
            validate_operation_type(item.operation_type)
        except ValueError as exc:
            results.append({"operation_id": item.operation_id or str(uuid4()), "status": "failed", "idempotent": False, "error": str(exc)})
            continue
        op_id = item.operation_id or str(uuid4())
        if item.entity_type not in ENTITY_HANDLERS:
            results.append({"operation_id": op_id, "status": "failed", "idempotent": False, "error": "Entité non synchronisable"})
            continue
        device = db.query(SyncDevice).filter(
            SyncDevice.school_id == current_user.school_id,
            SyncDevice.device_id == item.device_id,
        ).first()
        if device is None:
            results.append({"operation_id": op_id, "status": "failed", "idempotent": False, "error": "Appareil non enregistré"})
            continue
        if not _device_access(db, current_user, device):
            results.append({"operation_id": op_id, "status": "failed", "idempotent": False, "error": "Appareil attribué à un autre compte"})
            continue
        if not _sync_permission_allowed(db, current_user, item.entity_type, item.operation_type, item.payload):
            results.append({"operation_id": op_id, "status": "failed", "idempotent": False, "error": "Permission insuffisante pour cette entité"})
            continue

        existing = db.query(SyncOperation).filter(SyncOperation.operation_id == op_id).first()
        if existing:
            if existing.school_id != current_user.school_id:
                raise HTTPException(status_code=409, detail="Identifiant d'opération déjà utilisé par un autre établissement")
            results.append({"operation_id": op_id, "status": existing.status, "idempotent": True})
            continue

        version_key = _canonical_version_entity_id(db, current_user.school_id, item.entity_type, item.entity_id)
        version = db.query(SyncEntityVersion).filter(
            SyncEntityVersion.school_id == current_user.school_id,
            SyncEntityVersion.entity_type == item.entity_type,
            SyncEntityVersion.entity_id == version_key,
        ).first()
        current_version = version.version if version else 0
        status = "pending" if item.base_version == current_version else "conflict"
        error = None if status == "pending" else f"Conflit de version: client={item.base_version}, serveur={current_version}"
        op = SyncOperation(
            operation_id=op_id, school_id=current_user.school_id, device_id=item.device_id,
            user_id=current_user.id, entity_type=item.entity_type, entity_id=item.entity_id,
            operation_type=item.operation_type, base_version=item.base_version,
            server_version=current_version, payload=item.payload, status=status, error=error,
        )
        db.add(op)
        results.append({"operation_id": op_id, "status": status, "server_version": current_version, "idempotent": False})
    for item, result in zip(operations, results):
        if result.get("status") in {"pending", "conflict", "failed"}:
            _update_device_sync_state(
                db, current_user.school_id, item.device_id,
                "conflict" if result.get("status") == "conflict" else "pending",
                result.get("error"),
            )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Collision d'identifiant d'opération; réessayez avec le même operation_id")
    return {"accepted": len(results), "items": results}


@router.post("/apply/{operation_id}")
def apply_operation(operation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Applique une opération offline de façon transactionnelle et idempotente."""
    op = db.query(SyncOperation).filter(
        SyncOperation.operation_id == operation_id,
        SyncOperation.school_id == current_user.school_id,
    ).first()
    if op is None:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    if not _operation_access(db, current_user, op):
        raise HTTPException(status_code=403, detail="Opération créée par un autre compte")
    if not _sync_permission_allowed(db, current_user, op.entity_type, op.operation_type, op.payload):
        raise HTTPException(status_code=403, detail="Permission insuffisante pour appliquer cette opération")
    if op.status == "applied":
        return {"operation_id": op.operation_id, "status": "applied", "server_version": op.server_version, "idempotent": True}
    if op.status == "conflict":
        raise HTTPException(status_code=409, detail=op.error or "Opération en conflit")
    if op.status != "pending":
        raise HTTPException(status_code=409, detail=f"Opération non applicable: {op.status}")

    version_key = _canonical_version_entity_id(db, current_user.school_id, op.entity_type, op.entity_id)
    version = db.query(SyncEntityVersion).with_for_update().filter(
        SyncEntityVersion.school_id == current_user.school_id,
        SyncEntityVersion.entity_type == op.entity_type,
        SyncEntityVersion.entity_id == version_key,
    ).first()
    current_version = version.version if version else 0
    decision = decide_apply(op.base_version, current_version)
    if decision.status == "conflict":
        op.status = "conflict"
        op.server_version = current_version
        op.error = decision.error
        db.commit()
        raise HTTPException(status_code=409, detail=decision.error)

    if version is None:
        version = SyncEntityVersion(
            school_id=current_user.school_id,
            entity_type=op.entity_type,
            entity_id=op.entity_id,
            version=decision.new_version,
        )
        db.add(version)
    else:
        version.version = decision.new_version
    try:
        mutation = apply_business_mutation(db, op, current_version)
        # Pour une création, l'entité obtient un ID serveur. Le compteur doit
        # suivre cet ID canonique, sinon les autres postes ne convergent pas.
        if op.operation_type == "create" and mutation.get("entity_id") is not None and version.entity_id != str(mutation["entity_id"]):
            db.delete(version)
            db.flush()
            version = SyncEntityVersion(
                school_id=current_user.school_id, entity_type=op.entity_type,
                entity_id=str(mutation["entity_id"]), version=decision.new_version,
            )
            db.add(version)
    except ValueError as exc:
        db.rollback()
        op = db.query(SyncOperation).filter(
            SyncOperation.operation_id == operation_id,
            SyncOperation.school_id == current_user.school_id,
        ).first()
        op.status = "failed"
        op.error = str(exc)
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc))

    op.status = "applied"
    op.server_version = decision.new_version
    op.applied_at = datetime.now(timezone.utc)
    op.error = None
    _update_device_sync_state(db, current_user.school_id, op.device_id, "synchronized")
    db.commit()
    return {"operation_id": op.operation_id, "status": op.status, "server_version": op.server_version, "idempotent": False, "mutation": mutation}


@router.post("/apply-batch")
def apply_batch(operation_ids: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Applique plusieurs opérations dans l'ordre, sans perdre les succès précédents.

    Chaque opération reste transactionnelle et idempotente; une erreur sur une
    opération est retournée individuellement afin que le poste puisse reprendre
    exactement au même endroit après reconnexion.
    """
    if not operation_ids:
        raise HTTPException(status_code=422, detail="La liste des opérations est vide")
    if len(operation_ids) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 opérations par lot")
    results = []
    for operation_id in operation_ids:
        try:
            item = apply_operation(operation_id, current_user, db)
            results.append(item)
        except HTTPException as exc:
            status = "conflict" if exc.status_code == 409 and "conflit" in str(exc.detail).lower() else "failed"
            results.append({"operation_id": operation_id, "status": status, "http_status": exc.status_code, "error": exc.detail})
    return {"processed": len(results), "applied": sum(1 for x in results if x.get("status") == "applied"), "failed": sum(1 for x in results if x.get("status") == "failed"), "items": results}


@router.get("/conflicts")
def list_conflicts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste les conflits encore à traiter pour l'établissement courant."""
    query = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.status == "conflict",
    )
    if not _is_admin(db, current_user):
        query = query.filter(SyncOperation.user_id == current_user.id)
    rows = query.order_by(SyncOperation.created_at.asc()).all()
    return {"items": [{
        "operation_id": x.operation_id, "device_id": x.device_id,
        "entity_type": x.entity_type, "entity_id": x.entity_id,
        "operation_type": x.operation_type, "base_version": x.base_version,
        "server_version": x.server_version, "payload": x.payload,
        "error": x.error, "resolution": x.resolution,
        "resolved_at": x.resolved_at, "resolved_by_id": x.resolved_by_id,
    } for x in rows]}


@router.post("/conflicts/{operation_id}/resolve")
def resolve_conflict(operation_id: str, decision: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Résout explicitement un conflit: discard ou rebase puis nouvelle tentative."""
    choice = str(decision.get("resolution", "")).strip().lower()
    if choice not in {"discard", "rebase"}:
        raise HTTPException(status_code=422, detail="resolution doit être 'discard' ou 'rebase'")
    op = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.operation_id == operation_id,
    ).first()
    if op is None:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    if not _operation_access(db, current_user, op):
        raise HTTPException(status_code=403, detail="Opération créée par un autre compte")
    if op.status != "conflict":
        raise HTTPException(status_code=409, detail="Cette opération n'est pas en conflit")
    version_key = _canonical_version_entity_id(db, current_user.school_id, op.entity_type, op.entity_id)
    version = db.query(SyncEntityVersion).filter(
        SyncEntityVersion.school_id == current_user.school_id,
        SyncEntityVersion.entity_type == op.entity_type,
        SyncEntityVersion.entity_id == version_key,
    ).first()
    current_version = version.version if version else 0
    op.resolution = choice
    op.resolved_at = datetime.now(timezone.utc)
    op.resolved_by_id = current_user.id
    if choice == "discard":
        op.status = "failed"
        op.error = "Opération abandonnée lors de la résolution du conflit"
        _update_device_sync_state(db, current_user.school_id, op.device_id, "pending")
        db.commit()
        return {"operation_id": operation_id, "status": "discarded", "server_version": current_version}
    op.base_version = current_version
    op.server_version = current_version
    op.status = "pending"
    op.error = None
    _update_device_sync_state(db, current_user.school_id, op.device_id, "pending")
    db.commit()
    return {"operation_id": operation_id, "status": "rebased", "base_version": current_version}


@router.get("/devices/{device_id}/state")
def device_state(device_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """État de synchronisation exploitable directement par l'interface client."""
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == device_id
    ).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Appareil non enregistré")
    if not _device_access(db, current_user, device):
        raise HTTPException(status_code=403, detail="Appareil attribué à un autre compte")
    pending = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.device_id == device_id,
        SyncOperation.status.in_(["pending", "conflict"]),
    ).count()
    conflicts = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.device_id == device_id,
        SyncOperation.status == "conflict",
    ).count()
    return {
        "device_id": device_id, "status": device.status,
        "last_seen_at": device.last_seen_at, "last_sync_at": device.last_sync_at,
        "last_sync_status": device.last_sync_status, "last_sync_error": device.last_sync_error,
        "pending": pending, "conflicts": conflicts,
        "healthy": device.last_sync_status in {"synchronized", "pending"} and conflicts == 0,
    }


@router.get("/devices/{device_id}/queue")
def device_queue(device_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """État détaillé de la file d'un poste pour diagnostic/reprise offline."""
    device = db.query(SyncDevice).filter(SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Appareil non enregistré")
    rows = db.query(SyncOperation).filter(SyncOperation.school_id == current_user.school_id, SyncOperation.device_id == device_id).order_by(SyncOperation.id.desc()).limit(500).all()
    return {"device_id": device_id, "items": [{"operation_id": r.operation_id, "entity_type": r.entity_type, "entity_id": r.entity_id, "operation_type": r.operation_type, "status": r.status, "base_version": r.base_version, "server_version": r.server_version, "error": r.error, "created_at": r.created_at, "applied_at": r.applied_at} for r in rows]}


@router.get("/pull")
def pull(device_id: str, since_id: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retourne les mutations destinées à un poste, sans lui rediffuser ses propres opérations."""
    limit = min(max(limit, 1), 500)
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == device_id
    ).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Appareil non enregistré")
    if not _device_access(db, current_user, device):
        raise HTTPException(status_code=403, detail="Appareil attribué à un autre compte")
    acknowledged = db.query(SyncDeliveryAck.operation_id).filter(
        SyncDeliveryAck.school_id == current_user.school_id, SyncDeliveryAck.device_id == device_id
    ).subquery()
    rows = db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.id > since_id,
        SyncOperation.device_id != device_id,
        SyncOperation.status.in_(["pending", "applied"]),
        ~SyncOperation.operation_id.in_(acknowledged),
    ).order_by(SyncOperation.id.asc()).limit(limit).all()
    return {"items": [
        {"id": r.id, "operation_id": r.operation_id, "device_id": r.device_id,
         "entity_type": r.entity_type, "entity_id": r.entity_id,
         "server_entity_id": (db.query(SyncEntityIdentity.server_entity_id).filter(
             SyncEntityIdentity.school_id == r.school_id, SyncEntityIdentity.entity_type == r.entity_type,
             SyncEntityIdentity.client_entity_id == r.entity_id
         ).scalar()),
         "operation_type": r.operation_type,
         "base_version": r.base_version, "server_version": r.server_version,
         "payload": _pull_payload(db, r),
         "status": r.status, "created_at": r.created_at}
        for r in rows
    ], "next_id": rows[-1].id if rows else since_id}


@router.post("/ack")
def acknowledge(data: AckIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Enregistre les opérations effectivement reçues par un poste."""
    device = db.query(SyncDevice).filter(
        SyncDevice.school_id == current_user.school_id, SyncDevice.device_id == data.device_id
    ).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Appareil non enregistré")
    if not _device_access(db, current_user, device):
        raise HTTPException(status_code=403, detail="Appareil attribué à un autre compte")
    valid_ids = {r.operation_id for r in db.query(SyncOperation).filter(
        SyncOperation.school_id == current_user.school_id,
        SyncOperation.operation_id.in_(data.operation_ids),
    ).all()}
    created = 0
    for operation_id in valid_ids:
        exists = db.query(SyncDeliveryAck).filter(
            SyncDeliveryAck.school_id == current_user.school_id,
            SyncDeliveryAck.device_id == data.device_id,
            SyncDeliveryAck.operation_id == operation_id,
        ).first()
        if exists is None:
            db.add(SyncDeliveryAck(school_id=current_user.school_id, device_id=data.device_id, operation_id=operation_id))
            created += 1
    _update_device_sync_state(db, current_user.school_id, data.device_id, "synchronized")
    db.commit()
    return {"status": "ok", "device_id": data.device_id, "acknowledged": created, "ignored_unknown": len(data.operation_ids) - len(valid_ids)}
