from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.deps import get_current_user, require_permission
from app.models.communication_v3 import MessageCampaign, MessageDelivery, MessageRecipient, MessageTemplate, WhatsAppConfiguration
from app.models.notifications import CommunicationPreference
from app.models.security import User
from app.models.students import ClassMembership, Guardian, SchoolClass, Student, StudentGuardian
from app.schemas.communication_v3 import (
    CampaignCreate, CampaignOut, MessageDeliveryOut, MessageSend,
    MessageTemplateCreate, MessageTemplateOut,
)
from app.services.audit import log_action
from app.services.communication_engine import create_delivery, deliver, render_template
from app.services.cloud import enforce_subscription_feature, SubscriptionError

router = APIRouter(prefix="/api/connect", tags=["SIGMA Connect"])


def _school_guard(db: Session, current_user: User, school_id: int) -> None:
    if not current_user.is_superadmin and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Accès à cet établissement refusé")


def _guardians_for_target(db: Session, school_id: int, target_type: str, target_id: int | None) -> list[tuple[Guardian, int | None]]:
    if target_type == "guardian":
        g = db.get(Guardian, target_id) if target_id else None
        return [(g, None)] if g and g.school_id == school_id and g.is_active else []

    student_q = db.query(Student.id).filter(
        Student.school_id == school_id,
        Student.status == "active",
    )
    if target_type == "student":
        student_q = student_q.filter(Student.id == target_id)
    elif target_type == "school":
        # Toute l'école: le filtre de tenant est déjà appliqué ci-dessus.
        student_q = student_q
    elif target_type in {"class", "level", "stream"}:
        class_q = db.query(SchoolClass.id).filter(
            SchoolClass.school_id == school_id,
            SchoolClass.is_active.is_(True),
        )
        if target_type == "class":
            class_q = class_q.filter(SchoolClass.id == target_id)
        elif target_type == "level":
            class_q = class_q.filter(SchoolClass.level_id == target_id)
        else:
            class_q = class_q.filter(SchoolClass.stream_id == target_id)
        student_q = student_q.join(ClassMembership, ClassMembership.student_id == Student.id).filter(
            ClassMembership.class_id.in_(class_q.with_entities(SchoolClass.id).subquery()),
            ClassMembership.left_at.is_(None),
        ).distinct()
    else:
        raise HTTPException(status_code=422, detail="target_type invalide")

    # Une seule requête relationnelle pour tous les responsables ciblés.
    # On conserve le responsable principal quand il existe; sinon tous les liens.
    rows = (db.query(Guardian, StudentGuardian.student_id, StudentGuardian.is_primary_contact)
        .join(StudentGuardian, StudentGuardian.guardian_id == Guardian.id)
        .filter(
            Guardian.school_id == school_id,
            Guardian.is_active.is_(True),
            StudentGuardian.student_id.in_(student_q.subquery()),
        )
        .order_by(StudentGuardian.student_id.asc(), StudentGuardian.is_primary_contact.desc(), Guardian.id.asc())
        .all())

    grouped: dict[int, list[tuple[Guardian, int, bool]]] = {}
    for guardian, student_id, is_primary in rows:
        grouped.setdefault(student_id, []).append((guardian, student_id, bool(is_primary)))

    result: list[tuple[Guardian, int | None]] = []
    seen: set[tuple[int, int | None]] = set()
    for student_id, candidates in grouped.items():
        primaries = [item for item in candidates if item[2]]
        selected = primaries or candidates
        for guardian, linked_student_id, _ in selected:
            key = (guardian.id, linked_student_id)
            if key not in seen:
                result.append((guardian, linked_student_id))
                seen.add(key)
    return result


def _run_campaign(campaign_id: int) -> None:
    db = SessionLocal()
    try:
        campaign = db.get(MessageCampaign, campaign_id)
        if not campaign:
            return
        campaign.status = "sending"
        campaign.started_at = datetime.now(timezone.utc)
        db.commit()
        recipients = db.query(MessageRecipient).filter(MessageRecipient.campaign_id == campaign.id).all()
        for recipient in recipients:
            guardian = db.get(Guardian, recipient.guardian_id) if recipient.guardian_id else None
            if not guardian:
                recipient.status = "failed"
                continue
            delivery = create_delivery(
                db, school_id=campaign.school_id, guardian_id=guardian.id,
                student_id=recipient.student_id, campaign_id=campaign.id,
                recipient_id=recipient.id, body=campaign.body, channel=campaign.channel,
                title=campaign.name, send_now=True,
            )
            recipient.status = "sent" if delivery.status in {"sent", "delivered"} else "failed"
            if recipient.status == "sent":
                campaign.sent_count += 1
            else:
                campaign.failed_count += 1
            db.commit()
        campaign.status = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.exception("Échec de l'exécution de la campagne %s: %s", campaign_id, exc)
        if db.is_active:
            db.rollback()
        campaign = db.get(MessageCampaign, campaign_id)
        if campaign:
            campaign.status = "failed"
            campaign.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/send", response_model=MessageDeliveryOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("communication.sms.send"))])
def send_message(payload: MessageSend, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, payload.school_id)
    guardian = db.get(Guardian, payload.guardian_id)
    if not guardian or guardian.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Responsable légal introuvable")
    delivery = create_delivery(
        db, school_id=payload.school_id, guardian_id=guardian.id, student_id=payload.student_id,
        body=payload.body, channel=payload.channel, title=payload.title,
    )
    log_action(db, payload.school_id, current_user, "connect.send", "MessageDelivery", delivery.id,
               new_value=f"guardian={guardian.id};channel={delivery.channel};status={delivery.status}")
    return delivery


@router.get("/deliveries", response_model=list[MessageDeliveryOut], dependencies=[Depends(require_permission("communication.sms.view"))])
def list_deliveries(school_id: int, status_filter: str | None = None, limit: int = 100,
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, school_id)
    q = db.query(MessageDelivery).filter(MessageDelivery.school_id == school_id)
    if status_filter:
        q = q.filter(MessageDelivery.status == status_filter)
    return q.order_by(MessageDelivery.created_at.desc()).limit(min(max(limit, 1), 200)).all()


@router.post("/templates", response_model=MessageTemplateOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("communication.sms.send"))])
def create_template(payload: MessageTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, payload.school_id)
    item = MessageTemplate(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except Exception as exc:
        logger.exception("Échec de création du modèle de message %s: %s", payload.name, exc)
        db.rollback()
        raise HTTPException(status_code=409, detail="Un modèle portant ce nom existe déjà")
    db.refresh(item)
    return item


@router.get("/templates", response_model=list[MessageTemplateOut], dependencies=[Depends(require_permission("communication.sms.view"))])
def list_templates(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, school_id)
    return db.query(MessageTemplate).filter(MessageTemplate.school_id == school_id, MessageTemplate.is_active.is_(True)).order_by(MessageTemplate.name).all()


@router.get("/preferences/{guardian_id}")
def get_preferences(guardian_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = db.get(Guardian, guardian_id)
    if not guardian or guardian.school_id != current_user.school_id:
        raise HTTPException(status_code=404, detail="Responsable légal introuvable")
    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.school_id == current_user.school_id,
        CommunicationPreference.guardian_id == guardian_id,
    ).first()
    if not pref:
        return {"guardian_id": guardian_id, "push_enabled": True, "whatsapp_enabled": True,
                "sms_enabled": True, "email_enabled": True, "transactional_enabled": True,
                "marketing_enabled": False}
    return pref


@router.put("/preferences/{guardian_id}")
def update_preferences(guardian_id: int, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = db.get(Guardian, guardian_id)
    if not guardian or guardian.school_id != current_user.school_id:
        raise HTTPException(status_code=404, detail="Responsable légal introuvable")
    pref = db.query(CommunicationPreference).filter(
        CommunicationPreference.school_id == current_user.school_id,
        CommunicationPreference.guardian_id == guardian_id,
    ).first()
    if not pref:
        pref = CommunicationPreference(school_id=current_user.school_id, guardian_id=guardian_id)
        db.add(pref)
    for key in ("push_enabled", "whatsapp_enabled", "sms_enabled", "email_enabled", "transactional_enabled", "marketing_enabled"):
        if key in payload:
            setattr(pref, key, bool(payload[key]))
    db.commit()
    db.refresh(pref)
    return pref


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("communication.sms.send"))])
def create_campaign(payload: CampaignCreate, background_tasks: BackgroundTasks,
                    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, payload.school_id)
    targets = _guardians_for_target(db, payload.school_id, payload.target_type, payload.target_id)
    if not targets:
        raise HTTPException(status_code=422, detail="Aucun destinataire trouvé")
    campaign = MessageCampaign(
        school_id=payload.school_id, created_by_id=current_user.id, name=payload.name,
        channel=payload.channel, body=payload.body, target_type=payload.target_type,
        target_id=payload.target_id, status="queued", total_recipients=len(targets),
    )
    db.add(campaign)
    db.flush()
    for guardian, student_id in targets:
        recipient = MessageRecipient(
            campaign_id=campaign.id, guardian_id=guardian.id, student_id=student_id,
            recipient_phone=guardian.phone, recipient_email=guardian.email,
            recipient_label=f"{guardian.first_name} {guardian.last_name}",
        )
        db.add(recipient)
    db.commit()
    db.refresh(campaign)
    background_tasks.add_task(_run_campaign, campaign.id)
    log_action(db, payload.school_id, current_user, "connect.campaign.create", "MessageCampaign", campaign.id,
               new_value=f"destinataires={len(targets)}")
    return campaign


@router.get("/campaigns", response_model=list[CampaignOut], dependencies=[Depends(require_permission("communication.sms.view"))])
def list_campaigns(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, school_id)
    return db.query(MessageCampaign).filter(MessageCampaign.school_id == school_id).order_by(MessageCampaign.created_at.desc()).limit(100).all()


@router.post("/whatsapp/config", dependencies=[Depends(require_permission("administration.settings.modify"))])
def configure_whatsapp(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_guard(db, current_user, current_user.school_id)
    try:
        enforce_subscription_feature(db, current_user.school_id, "whatsapp")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    config = db.query(WhatsAppConfiguration).filter(WhatsAppConfiguration.school_id == current_user.school_id).first()
    if not config:
        config = WhatsAppConfiguration(school_id=current_user.school_id)
        db.add(config)
    for key in ("provider", "phone_number_id", "business_account_id", "access_token", "api_base_url", "is_active", "settings"):
        if key in payload:
            setattr(config, key, payload[key])
    db.commit()
    db.refresh(config)
    return {"id": config.id, "provider": config.provider, "phone_number_id": config.phone_number_id,
            "business_account_id": config.business_account_id, "api_base_url": config.api_base_url,
            "is_active": config.is_active, "has_access_token": bool(config.access_token)}
