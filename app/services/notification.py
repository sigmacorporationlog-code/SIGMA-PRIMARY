from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.notifications import Notification


def create_notification(
    db: Session,
    *,
    school_id: int,
    user_id: int,
    type: str,
    title: str,
    body: str,
    data: dict | None = None,
    commit: bool = True,
) -> Notification:
    item = Notification(
        school_id=school_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(item)
    if commit:
        db.commit()
        db.refresh(item)
    return item


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification
