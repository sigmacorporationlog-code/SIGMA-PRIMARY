from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing_v4 import SubscriptionInvoice
from app.models.payment_gateway import PaymentGatewayEvent
from app.services.billing_v4 import register_provider_payment


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not settings.PAYMENT_WEBHOOK_SECRET or not signature:
        return False
    supplied = signature.strip()
    if supplied.startswith("sha256="):
        supplied = supplied[7:]
    expected = hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def _payload_event_id(payload: dict[str, Any]) -> str:
    value = str(payload.get("external_event_id") or payload.get("event_id") or "").strip()
    if not value:
        raise ValueError("external_event_id requis")
    return value


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError("event_timestamp invalide")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def process_webhook(db: Session, raw_body: bytes, payload: dict[str, Any], signature: str | None, provider: str | None = None) -> dict:
    if not verify_signature(raw_body, signature):
        raise PermissionError("Signature webhook invalide")
    provider = (provider or settings.PAYMENT_WEBHOOK_PROVIDER).strip().lower() or "generic"
    event_id = _payload_event_id(payload)
    event_type = str(payload.get("event_type") or payload.get("type") or "payment").strip()[:60]
    received_at = datetime.now(timezone.utc)
    event_ts = _parse_timestamp(payload.get("event_timestamp"))
    if event_ts is not None:
        age = abs((received_at - event_ts).total_seconds())
        if age > settings.PAYMENT_WEBHOOK_MAX_AGE_SECONDS:
            raise ValueError("Événement webhook expiré")

    existing = db.query(PaymentGatewayEvent).filter(
        PaymentGatewayEvent.provider == provider,
        PaymentGatewayEvent.external_event_id == event_id,
    ).first()
    if existing:
        return {"id": existing.id, "status": existing.status, "duplicate": True, "payment_id": None}

    invoice_id = int(payload.get("invoice_id") or 0)
    amount = int(payload.get("amount_xaf") or 0)
    provider_reference = str(payload.get("provider_reference") or "").strip() or None
    event = PaymentGatewayEvent(
        provider=provider,
        external_event_id=event_id,
        event_type=event_type,
        status="received",
        invoice_id=invoice_id or None,
        amount_xaf=amount or None,
        provider_reference=provider_reference,
        signature_valid=True,
        received_at=received_at,
        payload_json=payload,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(PaymentGatewayEvent).filter(
            PaymentGatewayEvent.provider == provider,
            PaymentGatewayEvent.external_event_id == event_id,
        ).first()
        return {"id": existing.id, "status": existing.status, "duplicate": True, "payment_id": None}

    normalized_status = str(payload.get("status") or "paid").lower().strip()
    if normalized_status not in {"paid", "success", "successful", "completed"}:
        event.status = "ignored"
        event.processed_at = received_at
        db.commit()
        return {"id": event.id, "status": event.status, "duplicate": False, "payment_id": None}

    if invoice_id <= 0 or amount <= 0 or not provider_reference:
        event.status = "failed"
        event.error_message = "invoice_id, amount_xaf et provider_reference sont requis"
        db.commit()
        raise ValueError(event.error_message)

    invoice = db.get(SubscriptionInvoice, invoice_id)
    if not invoice:
        event.status = "failed"
        event.error_message = "Facture introuvable"
        db.commit()
        raise ValueError(event.error_message)

    try:
        payment = register_provider_payment(
            db,
            invoice_id=invoice_id,
            amount_xaf=amount,
            method=str(payload.get("method") or provider),
            provider_reference=provider_reference,
            external_event_id=f"{provider}:{event_id}",
        )
    except ValueError as exc:
        event.status = "failed"
        event.error_message = str(exc)
        db.commit()
        raise

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": event.id, "status": event.status, "duplicate": False, "payment_id": payment.id}
