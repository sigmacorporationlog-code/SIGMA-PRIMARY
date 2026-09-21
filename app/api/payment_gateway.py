from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.services.payment_gateway import process_webhook
from app.core.config import settings

router = APIRouter(prefix="/api/payments", tags=["Payment Gateway"])


@router.post("/webhooks/{provider}")
async def payment_webhook(provider: str, request: Request, x_signature: str | None = Header(default=None), db: Session = Depends(get_db)):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.WEBHOOK_MAX_BODY_BYTES:
                raise HTTPException(413, "Payload webhook trop volumineux")
        except ValueError:
            raise HTTPException(400, "Content-Length invalide")
    raw = await request.body()
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(413, "Payload webhook trop volumineux")
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(400, "Payload JSON invalide") from exc
    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload JSON doit être un objet")
    try:
        result = process_webhook(db, raw, payload, x_signature, provider)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result
