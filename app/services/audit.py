from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.security import AuditLog, User
from app.services.cloud import audit_chain_digest


def log_action(
    db: Session,
    school_id: int,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    ip_address: str | None = None,
    device: str | None = None,
    commit: bool = True,
) -> AuditLog:
    previous = db.query(AuditLog).filter(AuditLog.school_id == school_id).order_by(AuditLog.id.desc()).first()
    previous_hash = previous.entry_hash if previous and previous.entry_hash else (f"LEGACY:{previous.id}" if previous else "GENESIS")
    entry = AuditLog(
        school_id=school_id,
        user_id=user.id if user else None,
        at=datetime.now(timezone.utc),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        device=device,
        previous_hash=previous_hash,
    )
    db.add(entry)
    db.flush()
    entry.entry_hash = audit_chain_digest(entry, previous_hash)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
