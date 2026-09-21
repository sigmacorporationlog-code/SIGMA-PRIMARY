from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.notifications import Notification, PushSubscription
from app.models.security import User
from app.services.notification import mark_read

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(unread_only: bool = False, limit: int = 50,
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Notification).filter(Notification.school_id == current_user.school_id, Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    items = q.order_by(Notification.created_at.desc()).limit(min(max(limit, 1), 200)).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "body": n.body,
             "data": n.data, "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in items]


@router.post("/{notification_id}/read")
def read_notification(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.school_id != current_user.school_id or n.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    mark_read(db, n)
    return {"status": "ok"}


@router.post("/push/subscribe")
def subscribe_push(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    required = ("endpoint", "p256dh", "auth")
    if any(not payload.get(k) for k in required):
        raise HTTPException(status_code=422, detail="endpoint, p256dh et auth sont requis")
    existing = db.query(PushSubscription).filter(PushSubscription.user_id == current_user.id,
                                                  PushSubscription.endpoint == payload["endpoint"]).first()
    if existing:
        existing.p256dh = payload["p256dh"]
        existing.auth = payload["auth"]
        existing.user_agent = payload.get("user_agent")
        existing.is_active = True
    else:
        existing = PushSubscription(school_id=current_user.school_id, user_id=current_user.id,
                                    endpoint=payload["endpoint"], p256dh=payload["p256dh"],
                                    auth=payload["auth"], user_agent=payload.get("user_agent"))
        db.add(existing)
    db.commit()
    return {"status": "subscribed", "id": existing.id}
