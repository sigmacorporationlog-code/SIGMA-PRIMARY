from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.communication import SmsMessage
from app.models.communication_v3 import MessageDelivery, MessageRecipient
from app.models.notifications import CommunicationPreference, PushSubscription
from app.models.students import Guardian
from app.services.notification import create_notification
from app.services.sms_gateway import get_driver


CHANNEL_ORDER = ("push", "portal", "whatsapp", "sms")


def render_template(body: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    rendered = body
    for key, value in context.items():
        rendered = rendered.replace("{{" + key + "}}", "" if value is None else str(value))
    return rendered


def get_preferences(db: Session, school_id: int, guardian_id: int) -> CommunicationPreference:
    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.school_id == school_id,
        CommunicationPreference.guardian_id == guardian_id,
    ).first()
    if pref:
        return pref
    return CommunicationPreference(school_id=school_id, guardian_id=guardian_id)


def _channel_enabled(pref: CommunicationPreference, channel: str, transactional: bool) -> bool:
    if transactional and not pref.transactional_enabled:
        return False
    if channel == "push":
        return pref.push_enabled
    if channel == "portal":
        return True
    if channel == "whatsapp":
        return pref.whatsapp_enabled
    if channel == "sms":
        return pref.sms_enabled
    return False


def available_channels(db: Session, school_id: int, guardian: Guardian, requested: str = "auto", transactional: bool = True) -> list[str]:
    pref = get_preferences(db, school_id, guardian.id)
    channels = list(CHANNEL_ORDER) if requested == "auto" else [requested]
    result: list[str] = []
    for channel in channels:
        if not _channel_enabled(pref, channel, transactional):
            continue
        if channel in ("whatsapp", "sms") and not guardian.phone:
            continue
        if channel == "push":
            has_push = db.query(PushSubscription).filter(
                PushSubscription.school_id == school_id,
                PushSubscription.user_id == guardian.user_id,
                PushSubscription.is_active.is_(True),
            ).first() if guardian.user_id else None
            if not has_push:
                continue
        result.append(channel)
    return result


def _deliver_portal(db: Session, delivery: MessageDelivery, guardian: Guardian, title: str) -> None:
    if not guardian.user_id:
        raise RuntimeError("Le responsable n'a pas de compte portail")
    notification = create_notification(
        db,
        school_id=delivery.school_id,
        user_id=guardian.user_id,
        type="communication.message",
        title=title,
        body=delivery.body,
        data={"delivery_id": delivery.id, "student_id": delivery.student_id},
        commit=False,
    )
    delivery.provider_reference = f"portal-notification:{notification.id}"
    delivery.status = "delivered"
    delivery.sent_at = datetime.now(timezone.utc)
    delivery.delivered_at = delivery.sent_at


def _deliver_sms(db: Session, delivery: MessageDelivery, guardian: Guardian) -> None:
    if not guardian.phone:
        raise RuntimeError("Numéro de téléphone absent")
    driver = get_driver()
    ok, reference, error = driver.send(guardian.phone, delivery.body)
    delivery.attempts += 1
    delivery.provider_reference = reference
    delivery.error_message = error
    delivery.status = "sent" if ok else "failed"
    delivery.sent_at = datetime.now(timezone.utc) if ok else None


def _deliver_push(db: Session, delivery: MessageDelivery, guardian: Guardian) -> None:
    if not guardian.user_id:
        raise RuntimeError("Le responsable n'a pas de compte portail")
    from app.core.config import settings
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        raise RuntimeError("Web Push non configuré")
    subscription = db.query(PushSubscription).filter(
        PushSubscription.school_id == delivery.school_id,
        PushSubscription.user_id == guardian.user_id,
        PushSubscription.is_active.is_(True),
    ).first()
    if not subscription:
        raise RuntimeError("Aucun abonnement push actif")
    try:
        from pywebpush import webpush
    except ImportError as exc:
        raise RuntimeError("Le paquet pywebpush est requis pour activer Web Push") from exc
    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        },
        data=delivery.body,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT},
    )
    delivery.status = "sent"
    delivery.sent_at = datetime.now(timezone.utc)
    delivery.provider_reference = f"webpush:{subscription.id}"


def _deliver_whatsapp(delivery: MessageDelivery, guardian: Guardian) -> None:
    # L'adaptateur officiel Meta/BSP sera branché ici. Aucun WhatsApp Web
    # automation n'est utilisé : tant que le fournisseur n'est pas configuré,
    # on signale explicitement l'indisponibilité afin que le routeur puisse
    # continuer vers SMS.
    raise RuntimeError("WhatsApp officiel non configuré")


def deliver(db: Session, delivery: MessageDelivery, guardian: Guardian, *, title: str = "Message SIGMA") -> MessageDelivery:
    requested = delivery.channel
    channels = available_channels(db, delivery.school_id, guardian, requested)
    if not channels:
        delivery.status = "failed"
        delivery.error_message = "Aucun canal disponible"
        db.commit()
        return delivery

    # Pour auto, essayer séquentiellement jusqu'à succès. Pour un canal explicite,
    # le même mécanisme garantit un statut d'échec traçable.
    for channel in channels:
        delivery.channel = channel
        delivery.status = "sending"
        try:
            if channel == "portal":
                _deliver_portal(db, delivery, guardian, title)
            elif channel == "sms":
                _deliver_sms(db, delivery, guardian)
            elif channel == "whatsapp":
                _deliver_whatsapp(delivery, guardian)
            elif channel == "push":
                _deliver_push(db, delivery, guardian)
            if delivery.status in {"sent", "delivered"}:
                db.commit()
                return delivery
        except Exception as exc:
            delivery.status = "failed"
            delivery.error_message = str(exc)
            db.flush()
    db.commit()
    return delivery


def create_delivery(
    db: Session,
    *, school_id: int, guardian_id: int, body: str, channel: str = "auto",
    student_id: int | None = None, campaign_id: int | None = None,
    recipient_id: int | None = None, title: str = "Message SIGMA",
    send_now: bool = True,
) -> MessageDelivery:
    guardian = db.get(Guardian, guardian_id)
    if not guardian or guardian.school_id != school_id:
        raise ValueError("Responsable légal introuvable")
    delivery = MessageDelivery(
        school_id=school_id, guardian_id=guardian_id, student_id=student_id,
        campaign_id=campaign_id, recipient_id=recipient_id, channel=channel,
        body=body, status="queued",
    )
    db.add(delivery)
    db.flush()
    if send_now:
        deliver(db, delivery, guardian, title=title)
    return delivery
