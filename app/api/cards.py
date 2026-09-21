from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.documents import CardTemplate, IdCard
from app.models.students import Student, SchoolClass, ClassMembership
from app.schemas.documents import CardTemplateCreate, CardTemplateOut, IdCardIssue, IdCardOut, IdCardRevoke, IdCardLifecycleUpdate, IdCardBulkIssue
from app.services.audit import log_action
from app.services.card_engine import generate_access_code, render_card_html, render_card_page
from app.services.badge_engine import next_card_number, normalize_status, secure_qr_payload
from app.services.rate_limit import RateLimitExceeded, limiter

router = APIRouter(prefix="/api", tags=["Cartes"])


def _school_access(current_user: User, school_id: int) -> None:
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")


def _card_access(db: Session, current_user: User, card_id: int) -> IdCard:
    card = db.get(IdCard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    _school_access(current_user, card.school_id)
    return card


# ---------- Modèles de carte (édition libre par l'établissement) ----------

@router.post("/card-templates", response_model=CardTemplateOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_card_template(payload: CardTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_access(current_user, payload.school_id)
    if payload.is_default:
        db.query(CardTemplate).filter(
            CardTemplate.school_id == payload.school_id, CardTemplate.card_type == payload.card_type
        ).update({"is_default": False})

    template = CardTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/card-templates", response_model=list[CardTemplateOut], dependencies=[Depends(require_permission("cards.templates.view"))])
def list_card_templates(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_access(current_user, school_id)
    return db.query(CardTemplate).filter(CardTemplate.school_id == school_id, CardTemplate.is_active.is_(True)).all()


@router.patch("/card-templates/{template_id}", response_model=CardTemplateOut,
              dependencies=[Depends(require_permission("administration.settings.modify"))])
def edit_card_template(template_id: int, layout: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Édite la mise en page d'un modèle de carte (couleurs, champs affichés...)."""
    template = db.get(CardTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Modèle de carte introuvable")
    _school_access(current_user, template.school_id)
    template.layout = {**(template.layout or {}), **layout}
    db.commit()
    db.refresh(template)
    return template


# ---------- Émission de cartes ----------

@router.post("/id-cards", response_model=IdCardOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("cards.issue"))])
def issue_card(payload: IdCardIssue, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_access(current_user, payload.school_id)
    template = db.get(CardTemplate, payload.template_id)
    if template is None or template.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Modèle de carte introuvable")
    if payload.holder_type == "student" and payload.student_id is not None:
        student = db.get(Student, payload.student_id)
        if student is None or student.school_id != payload.school_id:
            raise HTTPException(status_code=404, detail="Élève introuvable")
    if payload.holder_type == "staff" and payload.user_id is not None:
        holder = db.get(User, payload.user_id)
        if holder is None or holder.school_id != payload.school_id:
            raise HTTPException(status_code=404, detail="Personnel introuvable")

    if payload.holder_type == "student" and payload.student_id is None:
        raise HTTPException(status_code=400, detail="student_id requis pour une carte élève")
    if payload.holder_type == "staff" and payload.user_id is None:
        raise HTTPException(status_code=400, detail="user_id requis pour une carte personnel")

    validity_years = payload.validity_years or settings.CARD_DEFAULT_VALIDITY_YEARS
    issued_at = date.today()
    expires_at = date(issued_at.year + validity_years, issued_at.month, issued_at.day) if validity_years else None

    card = IdCard(
        school_id=payload.school_id,
        template_id=template.id,
        holder_type=payload.holder_type,
        student_id=payload.student_id,
        user_id=payload.user_id,
        card_number=next_card_number(db, payload.school_id, (template.layout or {}).get("matricule_strategy", "year_sequence")),
        access_code=generate_access_code(),
        issued_at=issued_at,
        expires_at=expires_at,
        status="active",
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    log_action(db, payload.school_id, current_user, "card.issue", "IdCard", card.id, new_value=card.card_number)
    return card


@router.get("/id-cards", dependencies=[Depends(require_permission("cards.view"))])
def list_cards(school_id: int, student_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_access(current_user, school_id)
    if student_id is not None:
        student = db.get(Student, student_id)
        if student is None or student.school_id != school_id:
            raise HTTPException(status_code=404, detail="Élève introuvable")
    query = db.query(IdCard).filter(IdCard.school_id == school_id)
    if student_id:
        query = query.filter(IdCard.student_id == student_id)
    cards = query.order_by(IdCard.issued_at.desc()).all()

    result = []
    for card in cards:
        holder_name = "—"
        if card.holder_type == "student" and card.student_id:
            student = db.get(Student, card.student_id)
            if student:
                holder_name = f"{student.first_name} {student.last_name} ({student.matricule})"
        elif card.holder_type == "staff" and card.user_id:
            user = db.get(User, card.user_id)
            if user:
                holder_name = f"{user.first_name} {user.last_name}"
        result.append({
            "id": card.id, "card_number": card.card_number, "holder_type": card.holder_type,
            "holder_name": holder_name, "student_id": card.student_id, "user_id": card.user_id,
            "issued_at": card.issued_at, "expires_at": card.expires_at,
            "is_active": card.is_active, "status": card.status, "print_count": card.print_count,
        })
    return result


@router.post("/id-cards/{card_id}/revoke", dependencies=[Depends(require_permission("cards.issue"))])
def revoke_card(card_id: int, payload: IdCardRevoke, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Révoque une carte perdue/volée: elle ne doit plus être acceptée aux points d'accès."""
    card = _card_access(db, current_user, card_id)
    card.is_active = False
    card.status = "revoked"
    card.revoked_reason = payload.reason
    db.commit()
    log_action(db, card.school_id, current_user, "card.revoke", "IdCard", card.id, new_value=payload.reason)
    return {"status": "ok"}


@router.patch("/id-cards/{card_id}/lifecycle", response_model=IdCardOut, dependencies=[Depends(require_permission("cards.issue"))])
def update_card_lifecycle(card_id: int, payload: IdCardLifecycleUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = _card_access(db, current_user, card_id)
    try:
        new_status = normalize_status(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    card.status = new_status
    card.lifecycle_note = payload.note
    card.is_active = new_status in {"active", "printed", "delivered"}
    if new_status == "delivered":
        from datetime import datetime, timezone
        card.delivered_at = datetime.now(timezone.utc)
    if new_status == "revoked":
        card.revoked_reason = payload.note
    db.commit(); db.refresh(card)
    log_action(db, card.school_id, current_user, "card.lifecycle", "IdCard", card.id, new_value=new_status)
    return card


@router.post("/classes/{class_id}/id-cards/bulk-issue", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("cards.issue"))])
def bulk_issue_class_cards(class_id: int, payload: IdCardBulkIssue, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _school_access(current_user, payload.school_id)
    if class_id != payload.class_id:
        raise HTTPException(status_code=422, detail="class_id incohérent")
    school_class = db.get(SchoolClass, class_id)
    if school_class is None or school_class.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    template = db.get(CardTemplate, payload.template_id)
    if template is None or template.school_id != payload.school_id:
        raise HTTPException(status_code=404, detail="Modèle de carte introuvable")
    memberships = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)).all()
    issued = []
    validity_years = payload.validity_years or settings.CARD_DEFAULT_VALIDITY_YEARS
    issued_at = date.today()
    expires_at = date(issued_at.year + validity_years, issued_at.month, issued_at.day) if validity_years else None
    for membership in memberships:
        student = db.get(Student, membership.student_id)
        if not student or student.school_id != payload.school_id:
            continue
        existing = db.query(IdCard).filter(IdCard.student_id == student.id, IdCard.is_active.is_(True)).first()
        if existing:
            continue
        card = IdCard(school_id=payload.school_id, template_id=template.id, holder_type="student", student_id=student.id,
                      card_number=next_card_number(db, payload.school_id, (template.layout or {}).get("matricule_strategy", "year_sequence")),
                      access_code=generate_access_code(), issued_at=issued_at, expires_at=expires_at, status="active")
        db.add(card); db.flush(); issued.append(card.id)
    db.commit()
    return {"issued": len(issued), "card_ids": issued}


@router.get("/id-cards/verify/{access_code}")
def verify_card(request: Request, access_code: str, db: Session = Depends(get_db)):
    """Point de contrôle public: le QR ne contient qu'un token opaque.

    Cette route est volontairement non authentifiée pour permettre à un
    scanner de contrôler une carte, mais elle est limitée par IP et ne
    retourne aucune donnée nominative ni l'identifiant de l'établissement.
    """
    if len(access_code) > 128:
        raise HTTPException(status_code=422, detail="Code invalide")
    try:
        limiter.check(
            f"badge-verify:{request.client.host if request.client else 'unknown'}",
            limit=settings.BADGE_VERIFY_RATE_LIMIT,
            window_seconds=settings.BADGE_VERIFY_RATE_WINDOW_SECONDS,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(429, "Trop de vérifications. Réessayez plus tard.", headers={"Retry-After": str(settings.BADGE_VERIFY_RATE_WINDOW_SECONDS)}) from exc
    if access_code.startswith("SIGMA-BADGE:"):
        access_code = access_code.split(":", 1)[1]
    card = db.query(IdCard).filter(IdCard.access_code == access_code).first()
    if card is None or not card.is_active or card.status in {"lost", "damaged", "revoked", "replaced"}:
        return {"valid": False}
    if card.expires_at and card.expires_at < date.today():
        return {"valid": False, "reason": "expired"}
    return {"valid": True, "card_number": card.card_number, "status": card.status}


@router.get("/badge/verify/{access_code}", response_class=HTMLResponse)
def verify_badge_page(request: Request, access_code: str, db: Session = Depends(get_db)):
    result = verify_card(request, access_code, db)
    if not result.get("valid"):
        return HTMLResponse("<h1>Badge invalide</h1><p>Ce badge n'est plus valide.</p>", status_code=404)
    return HTMLResponse(f"<h1>Badge SIGMA valide</h1><p>Carte : {result['card_number']}</p><p>Statut : {result['status']}</p>")


# ---------- Rendu HTML imprimable ----------

def _build_card_html(db: Session, card: IdCard, template: CardTemplate) -> str:
    photo_data_uri = None

    if card.holder_type == "student":
        student = db.get(Student, card.student_id)
        holder_name = f"{student.first_name} {student.last_name}"
        membership = (
            db.query(ClassMembership)
            .filter(ClassMembership.student_id == student.id, ClassMembership.left_at.is_(None))
            .first()
        )
        class_name = membership.school_class.name if membership and membership.school_class else "—"
        fields = {"Matricule": student.matricule, "Classe": class_name}
        if student.birth_date:
            fields["Né(e) le"] = student.birth_date.isoformat()
        subtitle = "Carte scolaire"

        if (template.layout or {}).get("show_photo", True) and student.photo_path:
            photo_data_uri = _photo_as_data_uri(student.photo_path)
    else:
        user = db.get(User, card.user_id)
        holder_name = f"{user.first_name} {user.last_name}"
        fields = {"Identifiant": user.username}
        subtitle = "Carte d'accès - Personnel"

    from app.models.organization import School

    school = db.get(School, card.school_id)
    logo_uri = _asset_as_data_uri(school.logo_path) if school and school.logo_path else None
    stamp_uri = _asset_as_data_uri(school.official_stamp_path) if school and school.official_stamp_path else None
    phones = " / ".join([p for p in [school.phone, school.phone_secondary] if p]) if school else None

    return render_card_html(
        school_name=school.name if school else "SIGMA",
        holder_name=holder_name,
        subtitle=subtitle,
        fields=fields,
        card_number=card.card_number,
        access_code=card.access_code,
        expires_at=card.expires_at.isoformat() if card.expires_at else None,
        layout=template.layout or {},
        photo_data_uri=photo_data_uri,
        logo_data_uri=logo_uri, stamp_data_uri=stamp_uri,
        ministry_name=school.ministry_name if school else None, school_phones=phones,
    )


def _asset_as_data_uri(relative_path: str) -> str | None:
    import base64
    from app.services.media import resolve_media_path
    path=resolve_media_path(relative_path)
    if not path.exists(): return None
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _photo_as_data_uri(relative_path: str) -> str | None:
    """Encode la photo de l'élève (déjà normalisée en JPEG par
    app/services/media.py) en data URI pour l'intégrer directement dans le
    HTML imprimable de la carte, sans dépendre d'une URL accessible."""
    import base64

    from app.services.media import resolve_media_path

    path = resolve_media_path(relative_path)
    if not path.exists():
        return None
    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


@router.get("/id-cards/{card_id}/print", response_class=HTMLResponse,
            dependencies=[Depends(require_permission("cards.issue"))])
def print_card(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = _card_access(db, current_user, card_id)
    template = db.get(CardTemplate, card.template_id)
    if template is None or template.school_id != card.school_id:
        raise HTTPException(status_code=404, detail="Modèle de carte introuvable")

    card.print_count += 1
    from datetime import datetime, timezone
    card.last_printed_at = datetime.now(timezone.utc)
    db.commit()

    html = _build_card_html(db, card, template)
    return HTMLResponse(render_card_page([html]))


@router.get("/classes/{class_id}/id-cards/print", response_class=HTMLResponse,
            dependencies=[Depends(require_permission("cards.issue"))])
def print_class_cards(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_class = db.get(SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    _school_access(current_user, school_class.school_id)
    """Impression en lot: toutes les cartes actives des élèves d'une classe."""
    memberships = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)).all()
    student_ids = [m.student_id for m in memberships]

    cards_html = []
    for student_id in student_ids:
        card = (
            db.query(IdCard)
            .filter(IdCard.student_id == student_id, IdCard.is_active.is_(True))
            .order_by(IdCard.issued_at.desc())
            .first()
        )
        if card is None or card.school_id != school_class.school_id:
            continue
        template = db.get(CardTemplate, card.template_id)
        if template is None or template.school_id != school_class.school_id:
            continue
        cards_html.append(_build_card_html(db, card, template))

    if not cards_html:
        raise HTTPException(status_code=404, detail="Aucune carte active trouvée pour cette classe")

    return HTMLResponse(render_card_page(cards_html))


@router.get("/id-cards/{card_id}/download.pdf", dependencies=[Depends(require_permission("cards.view"))])
def download_card_pdf(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.card_pdf import generate_student_card_pdf
    card=_card_access(db, current_user, card_id)
    if card.holder_type!="student": raise HTTPException(status_code=404, detail="Carte élève introuvable")
    content=generate_student_card_pdf(db,card)
    return Response(content=content,media_type="application/pdf",headers={"Content-Disposition":f"attachment; filename={card.card_number}.pdf"})


@router.get("/classes/{class_id}/id-cards/download.pdf", dependencies=[Depends(require_permission("cards.view"))])
def download_class_cards_pdf(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.card_pdf import generate_class_cards_pdf
    from app.models.students import SchoolClass
    school_class = db.get(SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="Classe introuvable")
    _school_access(current_user, school_class.school_id)
    cards=[]
    for m in db.query(ClassMembership).filter(ClassMembership.class_id==class_id,ClassMembership.left_at.is_(None)).all():
        card=db.query(IdCard).filter(IdCard.student_id==m.student_id,IdCard.is_active.is_(True)).order_by(IdCard.issued_at.desc()).first()
        if card: cards.append(card)
    if not cards: raise HTTPException(status_code=404,detail="Aucune carte active trouvée")
    content=generate_class_cards_pdf(db,cards)
    return Response(content=content,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=cartes_classe.pdf"})
