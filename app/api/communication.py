from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.communication import SmsMessage
from app.models.students import ClassMembership, Student, StudentGuardian, Guardian
from app.models.finance import Invoice
from app.schemas.communication import SmsSendToPhone, SmsSendToClass, SmsSendToUnpaid, SmsMessageOut, SmsSendToGuardian, SmsSendToTarget
from app.services.audit import log_action
from app.services.sms_gateway import get_driver

router = APIRouter(prefix="/api", tags=["Communication"])


def _dispatch(db: Session, school_id: int, user: User, phone: str, body: str,
              recipient_label: str | None = None, student_id: int | None = None,
              guardian_id: int | None = None, campaign_label: str | None = None) -> SmsMessage:
    message = SmsMessage(
        school_id=school_id, sent_by_id=user.id, recipient_phone=phone, recipient_label=recipient_label,
        student_id=student_id, guardian_id=guardian_id, body=body, campaign_label=campaign_label,
    )
    db.add(message)
    db.flush()

    driver = get_driver()
    try:
        ensure_provider_allowed(driver)
    except RuntimeError as exc:
        message.status = "failed"
        message.error_message = str(exc)
        message.attempts += 1
        db.commit()
        raise HTTPException(status_code=503, detail="Fournisseur SMS non configuré pour cet environnement") from exc
    ok, reference, error = driver.send(phone, body)
    message.attempts += 1
    message.status = ("simulated" if ok and driver.is_simulation else "sent") if ok else "failed"
    message.provider_reference = reference
    message.error_message = error
    if ok:
        message.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


@router.get("/sms/status", dependencies=[Depends(require_permission("communication.sms.view"))])
def sms_provider_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.deps import assert_school_access
    assert_school_access(current_user, current_user.school_id)
    driver = get_driver()
    return {
        "provider": driver.name,
        "simulation": bool(driver.is_simulation),
        "environment": settings.ENV,
        "production_ready": not (settings.ENV.lower() == "production" and driver.is_simulation and not settings.SMS_ALLOW_SIMULATION_IN_PRODUCTION),
    }


@router.post("/sms/send", response_model=SmsMessageOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("communication.sms.send"))])
def send_sms_to_phone(payload: SmsSendToPhone, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, payload.school_id)
    message = _dispatch(
        db, payload.school_id, current_user, payload.phone, payload.body,
        recipient_label=payload.recipient_label, campaign_label=payload.campaign_label,
    )
    log_action(db, payload.school_id, current_user, "sms.send", "SmsMessage", message.id,
               new_value=f"{payload.phone}: {message.status}")
    return message


@router.post("/sms/send-to-class", response_model=list[SmsMessageOut],
             dependencies=[Depends(require_permission("communication.sms.send"))])
def send_sms_to_class(payload: SmsSendToClass, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, payload.school_id)
    school_class = __import__("app.models.students", fromlist=["SchoolClass"]).SchoolClass
    cls = db.get(school_class, payload.class_id)
    if not cls or cls.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    """Ex: 'Tous les parents de 3e C' (cahier des charges §33)."""
    memberships = db.query(ClassMembership).filter(
        ClassMembership.class_id == payload.class_id, ClassMembership.left_at.is_(None)
    ).all()

    sent = []
    for membership in memberships:
        links = db.query(StudentGuardian).filter(StudentGuardian.student_id == membership.student_id).all()
        student = db.get(Student, membership.student_id)
        for link in links:
            guardian = db.get(Guardian, link.guardian_id)
            if not guardian or not guardian.phone:
                continue
            message = _dispatch(
                db, payload.school_id, current_user, guardian.phone, payload.body,
                recipient_label=f"{guardian.first_name} {guardian.last_name} ({guardian.relationship_type})",
                student_id=student.id, guardian_id=guardian.id, campaign_label=payload.campaign_label,
            )
            sent.append(message)

    log_action(db, payload.school_id, current_user, "sms.send_to_class", "SmsMessage",
               new_value=f"classe={payload.class_id} destinataires={len(sent)}")
    return sent


@router.post("/sms/send-to-unpaid", response_model=list[SmsMessageOut],
             dependencies=[Depends(require_permission("communication.sms.send"))])
def send_sms_to_unpaid(payload: SmsSendToUnpaid, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, payload.school_id)
    """Ex: 'Parents dont les frais sont impayés' (cahier des charges §33)."""
    from app.models.organization import AcademicYear
    year = db.get(AcademicYear, payload.academic_year_id)
    if not year or year.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Année scolaire introuvable")
    invoices = db.query(Invoice).join(Student, Invoice.student_id == Student.id).filter(
        Invoice.academic_year_id == payload.academic_year_id,
        Student.school_id == payload.school_id,
        Invoice.status.in_(["pending", "partially_paid", "overdue"]),
    ).all()
    student_ids = {inv.student_id for inv in invoices}

    sent = []
    for student_id in student_ids:
        student = db.get(Student, student_id)
        links = db.query(StudentGuardian).filter(
            StudentGuardian.student_id == student_id, StudentGuardian.is_primary_contact.is_(True)
        ).all()
        if not links:
            links = db.query(StudentGuardian).filter(StudentGuardian.student_id == student_id).all()

        for link in links:
            guardian = db.get(Guardian, link.guardian_id)
            if not guardian or not guardian.phone:
                continue
            message = _dispatch(
                db, payload.school_id, current_user, guardian.phone, payload.body,
                recipient_label=f"{guardian.first_name} {guardian.last_name}",
                student_id=student.id, guardian_id=guardian.id, campaign_label=payload.campaign_label,
            )
            sent.append(message)
            break  # un seul SMS par élève, au contact principal

    log_action(db, payload.school_id, current_user, "sms.send_to_unpaid", "SmsMessage",
               new_value=f"destinataires={len(sent)}")
    return sent


@router.get("/sms/logs", response_model=list[SmsMessageOut],
           dependencies=[Depends(require_permission("communication.sms.view"))])
def list_sms_logs(school_id: int, status_filter: str | None = None, limit: int = 100,
                   db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, school_id)
    query = db.query(SmsMessage).filter(SmsMessage.school_id == school_id)
    if status_filter:
        query = query.filter(SmsMessage.status == status_filter)
    return query.order_by(SmsMessage.created_at.desc()).limit(limit).all()


@router.post("/sms/{message_id}/retry", response_model=SmsMessageOut,
             dependencies=[Depends(require_permission("communication.sms.send"))])
def retry_sms(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    message = db.get(SmsMessage, message_id)
    if message is None or (message.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Message introuvable")
    if message.status == "sent":
        return message

    driver = get_driver()
    ok, reference, error = driver.send(message.recipient_phone, message.body)
    message.attempts += 1
    message.status = "sent" if ok else "failed"
    message.provider_reference = reference
    message.error_message = error
    if ok:
        message.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


@router.post("/sms/send-to-guardian", response_model=SmsMessageOut, dependencies=[Depends(require_permission("communication.sms.send"))])
def send_sms_to_guardian(payload: SmsSendToGuardian, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, payload.school_id)
    guardian=db.get(Guardian,payload.guardian_id)
    if not guardian or guardian.school_id!=payload.school_id or not guardian.phone: raise HTTPException(status_code=404,detail="Parent/tuteur introuvable ou sans téléphone")
    student_id=None; link=db.query(StudentGuardian).filter(StudentGuardian.guardian_id==guardian.id,StudentGuardian.is_primary_contact.is_(True)).first()
    if link: student_id=link.student_id
    return _dispatch(db,payload.school_id,current_user,guardian.phone,payload.body,f"{guardian.first_name} {guardian.last_name}",student_id,guardian.id,payload.campaign_label)


@router.post("/sms/send-to-target", response_model=list[SmsMessageOut], dependencies=[Depends(require_permission("communication.sms.send"))])
def send_sms_to_target(payload: SmsSendToTarget, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.deps import assert_school_access
    assert_school_access(current_user, payload.school_id)
    q=db.query(Student).filter(Student.school_id==payload.school_id,Student.status=="active")
    if payload.target_type=="class":
        ids=[m.student_id for m in db.query(ClassMembership).filter(ClassMembership.class_id==payload.target_id,ClassMembership.left_at.is_(None)).all()]; q=q.filter(Student.id.in_(ids or [-1]))
    elif payload.target_type in ("level","stream"):
        from app.models.students import SchoolClass
        cq=db.query(SchoolClass.id)
        if payload.target_type=="level": cq=cq.filter(SchoolClass.level_id==payload.target_id)
        else: cq=cq.filter(SchoolClass.stream_id==payload.target_id)
        cids=[x[0] for x in cq.filter(SchoolClass.school_id==payload.school_id,SchoolClass.is_active.is_(True)).all()]
        ids=[m.student_id for m in db.query(ClassMembership).filter(ClassMembership.class_id.in_(cids or [-1]),ClassMembership.left_at.is_(None)).all()]; q=q.filter(Student.id.in_(ids or [-1]))
    elif payload.target_type!="school": raise HTTPException(status_code=400,detail="Cible invalide")
    sent=[]
    for student in q.all():
        link=db.query(StudentGuardian).filter(StudentGuardian.student_id==student.id,StudentGuardian.is_primary_contact.is_(True)).first() or db.query(StudentGuardian).filter(StudentGuardian.student_id==student.id).first()
        if link and link.guardian and link.guardian.phone:
            sent.append(_dispatch(db,payload.school_id,current_user,link.guardian.phone,payload.body,f"{link.guardian.first_name} {link.guardian.last_name}",student.id,link.guardian.id,payload.campaign_label))
    return sent
