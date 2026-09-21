from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.students import Student, SchoolClass, Guardian, StudentGuardian, ClassMembership, Level, Stream
from app.schemas.students import (
    StudentCreate, StudentOut, SchoolClassCreate, SchoolClassUpdate, SchoolClassOut,
    LevelUpdate, StreamUpdate,
    ClassMembershipCreate, EnrollmentCreate, EnrollmentTransfer, GuardianCreate, GuardianOut, GuardianUpdate, StudentGuardianLink,
)
from app.services.audit import log_action
from app.services.cloud import enforce_subscription_capacity, SubscriptionError
from app.services.media import save_student_photo, resolve_media_path, delete_student_photo
from app.services.matricule import next_matricule
from app.services.excel_engine import export_students_xlsx, build_student_import_template, parse_students_import, StudentImportRowError
from app.services.pdf_engine import generate_students_list_pdf, generate_enrollment_certificate_pdf, generate_student_dossier_pdf

router = APIRouter(prefix="/api", tags=["Élèves"])


# ---------- Élèves ----------

@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("students.create"))])
def create_student(payload: StudentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Établissement non autorisé")
    try:
        enforce_subscription_capacity(db, payload.school_id, "students")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    data = payload.model_dump()
    class_id = data.pop("class_id", None); academic_year_id = data.pop("academic_year_id", None)
    matricule = data.pop("matricule", None)
    if not matricule:
        try:
            matricule = next_matricule(db, payload.school_id, class_id=class_id, academic_year_id=academic_year_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        matricule = matricule.strip().upper()
        if db.query(Student).filter(Student.school_id == payload.school_id, Student.matricule == matricule).first():
            raise HTTPException(status_code=400, detail="Ce matricule existe déjà dans l'établissement")
    data["matricule"] = matricule
    school_class = None
    if class_id:
        school_class = db.get(SchoolClass, class_id)
        if not school_class or school_class.school_id != payload.school_id:
            raise HTTPException(status_code=400, detail="Classe invalide pour cet établissement")
        year_id = academic_year_id or school_class.academic_year_id
        if year_id != school_class.academic_year_id:
            raise HTTPException(status_code=400, detail="La classe n'appartient pas à l'année scolaire sélectionnée")
        active_count = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)).count()
        if school_class.capacity is not None and active_count >= school_class.capacity:
            raise HTTPException(status_code=409, detail="La capacité de cette classe est atteinte")

    guardian_data = {
        "first_name": data.pop("guardian_first_name", None), "last_name": data.pop("guardian_last_name", None),
        "relationship_type": data.pop("guardian_relationship", None), "phone": data.pop("guardian_phone", None),
        "email": data.pop("guardian_email", None), "address": data.pop("guardian_address", None),
    }
    student = Student(**data)
    db.add(student); db.flush()
    if guardian_data["first_name"] or guardian_data["last_name"] or guardian_data["phone"]:
        guardian = Guardian(school_id=student.school_id, first_name=guardian_data["first_name"] or "", last_name=guardian_data["last_name"] or "", relationship_type=guardian_data["relationship_type"] or "tuteur", phone=guardian_data["phone"], email=guardian_data["email"], address=guardian_data["address"])
        db.add(guardian); db.flush(); db.add(StudentGuardian(student_id=student.id, guardian_id=guardian.id, is_primary_contact=True))
    if class_id:
        db.add(ClassMembership(student_id=student.id, class_id=class_id, academic_year_id=school_class.academic_year_id, enrolled_at=date.today()))
    db.commit(); db.refresh(student)
    log_action(db, payload.school_id, current_user, "student.create", "Student", student.id,
               new_value=f"{payload.first_name} {payload.last_name}")
    return student


@router.get("/students", response_model=list[StudentOut], dependencies=[Depends(require_permission("students.view"))])
def list_students(school_id: int, status_filter: str | None = None, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    query = db.query(Student).filter(Student.school_id == school_id)
    if status_filter:
        query = query.filter(Student.status == status_filter)
    return query.all()


@router.get("/students/{student_id}/profile", dependencies=[Depends(require_permission("students.view"))])
def student_profile(student_id: int, academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Dossier administratif consolidé: identité, classe courante, historique et responsables."""
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")

    memberships_q = db.query(ClassMembership).filter(ClassMembership.student_id == student_id)
    if academic_year_id:
        memberships_q = memberships_q.filter(ClassMembership.academic_year_id == academic_year_id)
    memberships = memberships_q.order_by(ClassMembership.enrolled_at.desc()).all()
    current = next((m for m in memberships if m.left_at is None), None)
    guardians = []
    for link in student.guardian_links:
        g = link.guardian
        if g and g.school_id == current_user.school_id:
            guardians.append({
                "id": g.id, "first_name": g.first_name, "last_name": g.last_name,
                "relationship_type": g.relationship_type, "phone": g.phone, "email": g.email,
                "address": g.address, "can_pick_up_child": g.can_pick_up_child,
                "is_primary_contact": link.is_primary_contact,
            })
    return {
        "student": {
            "id": student.id, "school_id": student.school_id, "matricule": student.matricule,
            "first_name": student.first_name, "last_name": student.last_name,
            "birth_date": student.birth_date.isoformat() if student.birth_date else None,
            "birth_place": student.birth_place, "sex": student.sex, "nationality": student.nationality,
            "address": student.address, "status": student.status, "is_active": student.is_active,
            "photo_path": student.photo_path,
        },
        "current_enrollment": ({
            "id": current.id, "class_id": current.class_id,
            "class_name": current.school_class.name if current.school_class else None,
            "academic_year_id": current.academic_year_id, "enrolled_at": current.enrolled_at.isoformat(),
            "enrollment_type": current.enrollment_type,
        } if current else None),
        "enrollment_history": [{
            "id": m.id, "class_id": m.class_id, "class_name": m.school_class.name if m.school_class else None,
            "academic_year_id": m.academic_year_id, "enrolled_at": m.enrolled_at.isoformat(),
            "left_at": m.left_at.isoformat() if m.left_at else None, "enrollment_type": m.enrollment_type,
            "current": m.left_at is None,
        } for m in memberships],
        "guardians": guardians,
        "primary_guardian": next((g for g in guardians if g["is_primary_contact"]), None),
    }


@router.get("/students/{student_id}/360", dependencies=[Depends(require_permission("students.view"))])
def student_360(student_id: int, academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Dossier Élève 360 V3: administratif, pédagogie, assiduité, finance et documents."""
    from app.services.student_360 import build_student_360
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    return build_student_360(db, student, academic_year_id)


@router.get("/students/{student_id}", response_model=StudentOut, dependencies=[Depends(require_permission("students.view"))])
def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    return student


@router.patch("/students/{student_id}/status", dependencies=[Depends(require_permission("students.modify"))])
def change_student_status(student_id: int, new_status: str, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """new_status: active/transferred/dropped_out/excluded/graduated/conditional"""
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    allowed_statuses = {"active", "transferred", "dropped_out", "excluded", "graduated", "conditional"}
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=422, detail=f"Statut élève invalide. Valeurs autorisées: {', '.join(sorted(allowed_statuses))}")
    old_status = student.status
    if new_status == "active" and old_status != "active":
        try:
            enforce_subscription_capacity(db, student.school_id, "students")
        except SubscriptionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    student.status = new_status
    if new_status != "active":
        for m in db.query(ClassMembership).filter(ClassMembership.student_id == student.id, ClassMembership.left_at.is_(None)).all():
            m.left_at = date.today()
    db.commit()
    log_action(db, student.school_id, current_user, "student.status.change", "Student", student.id,
               old_value=old_status, new_value=new_status)
    return {"status": "ok"}


@router.post("/students/{student_id}/withdraw", dependencies=[Depends(require_permission("students.modify"))])
def withdraw_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    student.status = "transferred"
    for m in db.query(ClassMembership).filter(ClassMembership.student_id == student.id, ClassMembership.left_at.is_(None)).all(): m.left_at = date.today()
    db.commit(); log_action(db, student.school_id, current_user, "student.withdraw", "Student", student.id)
    return {"status":"ok", "student_status":student.status}


def _current_class_name(db: Session, student_id: int) -> str | None:
    membership = (
        db.query(ClassMembership)
        .filter(ClassMembership.student_id == student_id, ClassMembership.left_at.is_(None))
        .order_by(ClassMembership.enrolled_at.desc())
        .first()
    )
    if membership is None:
        return None
    school_class = db.get(SchoolClass, membership.class_id)
    return school_class.name if school_class else None



@router.get("/students/matricule/preview", dependencies=[Depends(require_permission("students.view"))])
def preview_matricule(class_id: int | None = None, academic_year_id: int | None = None,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        value = next_matricule(db, current_user.school_id, class_id=class_id, academic_year_id=academic_year_id)
        db.rollback()  # preview: ne consomme jamais la séquence.
        return {"matricule": value}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

# ---------- Grille élèves (vue enrichie pour l'interface: photo, classe) ----------

@router.get("/students/grid", dependencies=[Depends(require_permission("students.view"))])
def students_grid(
    school_id: int, search: str | None = None, class_id: int | None = None,
    status_filter: str | None = None, limit: int = 50, offset: int = 0,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """
    Vue "grille" pour l'interface: pagination, recherche par nom/matricule,
    filtre par classe, et indication de présence d'une photo — pensée pour
    alimenter directement un tableau élèves avec bouton d'import de photo.
    """
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    query = db.query(Student).filter(Student.school_id == school_id, Student.is_active.is_(True))
    if status_filter:
        query = query.filter(Student.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Student.first_name.ilike(like)) | (Student.last_name.ilike(like)) | (Student.matricule.ilike(like))
        )
    if class_id:
        student_ids = [
            m.student_id for m in db.query(ClassMembership).filter(
                ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)
            ).all()
        ]
        query = query.filter(Student.id.in_(student_ids or [-1]))

    total = query.count()
    students = query.order_by(Student.last_name, Student.first_name).offset(offset).limit(limit).all()

    items = [
        {
            "id": s.id,
            "matricule": s.matricule,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "sex": s.sex,
            "status": s.status,
            "class_name": _current_class_name(db, s.id),
            "has_photo": bool(s.photo_path),
            "birth_date": s.birth_date.isoformat() if s.birth_date else None,
            "birth_place": s.birth_place,
            "address": s.address,
            "guardian_name": next((f"{l.guardian.first_name} {l.guardian.last_name}" for l in s.guardian_links if l.is_primary_contact), None),
            "guardian_phone": next((l.guardian.phone for l in s.guardian_links if l.is_primary_contact), None),
        }
        for s in students
    ]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/students/{student_id}/documents/enrollment-certificate.pdf", dependencies=[Depends(require_permission("students.view"))])
def enrollment_certificate(student_id: int, academic_year_id: int | None = None,
                           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Génère l'attestation d'inscription de l'inscription active sélectionnée."""
    from app.models.organization import School, AcademicYear
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    q = db.query(ClassMembership).filter(ClassMembership.student_id == student_id, ClassMembership.left_at.is_(None))
    if academic_year_id:
        q = q.filter(ClassMembership.academic_year_id == academic_year_id)
    membership = q.order_by(ClassMembership.enrolled_at.desc()).first()
    if not membership or not membership.school_class:
        raise HTTPException(status_code=404, detail="Aucune inscription active")
    school = db.get(School, student.school_id)
    year = db.get(AcademicYear, membership.academic_year_id)
    primary = next((l.guardian for l in student.guardian_links if l.is_primary_contact and l.guardian), None)
    content = generate_enrollment_certificate_pdf(
        school_name=school.name if school else "SIGMA",
        school_address=school.address if school else None,
        school_phone=school.phone if school else None,
        academic_year_label=year.label if year else str(membership.academic_year_id),
        student_name=f"{student.first_name} {student.last_name}",
        student_matricule=student.matricule,
        class_name=membership.school_class.name,
        enrolled_at=membership.enrolled_at.strftime("%d/%m/%Y"),
        guardian_name=(f"{primary.first_name} {primary.last_name}" if primary else None),
    )
    log_action(db, student.school_id, current_user, "document.enrollment_certificate", "Student", student.id)
    # inline: ouverture directe + bouton Imprimer du navigateur (voir
    # justification détaillée sur le reçu de paiement dans finance.py).
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="attestation_inscription_{student.matricule}.pdf"'})


@router.get("/students/{student_id}/documents/dossier.pdf", dependencies=[Depends(require_permission("students.view"))])
def student_dossier_pdf(student_id: int, academic_year_id: int | None = None,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Dossier administratif imprimable, incluant identité, responsables et historique."""
    from app.models.organization import School, AcademicYear
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    q = db.query(ClassMembership).filter(ClassMembership.student_id == student_id)
    if academic_year_id:
        q = q.filter(ClassMembership.academic_year_id == academic_year_id)
    memberships = q.order_by(ClassMembership.enrolled_at.desc()).all()
    current = next((m for m in memberships if m.left_at is None), None)
    guardians = []
    for link in student.guardian_links:
        if link.guardian and link.guardian.school_id == current_user.school_id:
            g=link.guardian
            guardians.append({"id":g.id,"first_name":g.first_name,"last_name":g.last_name,"relationship_type":g.relationship_type,"phone":g.phone,"email":g.email,"address":g.address,"can_pick_up_child":g.can_pick_up_child,"is_primary_contact":link.is_primary_contact})
    school = db.get(School, student.school_id)
    year_id = current.academic_year_id if current else academic_year_id
    year = db.get(AcademicYear, year_id) if year_id else None
    student_dict={"matricule":student.matricule,"first_name":student.first_name,"last_name":student.last_name,"birth_date":student.birth_date.isoformat() if student.birth_date else None,"birth_place":student.birth_place,"sex":student.sex,"nationality":student.nationality,"address":student.address,"status":student.status}
    history=[{"academic_year_id":m.academic_year_id,"class_name":m.school_class.name if m.school_class else None,"enrolled_at":m.enrolled_at.isoformat(),"left_at":m.left_at.isoformat() if m.left_at else None,"enrollment_type":m.enrollment_type} for m in memberships]
    content=generate_student_dossier_pdf(school_name=school.name if school else "SIGMA",academic_year_label=year.label if year else "—",student=student_dict,current_enrollment=({"class_name":current.school_class.name} if current and current.school_class else None),guardians=guardians,enrollment_history=history)
    log_action(db, student.school_id, current_user, "document.student_dossier", "Student", student.id)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=dossier_{student.matricule}.pdf"})


# ---------- Photo de l'élève ----------

@router.post("/students/{student_id}/photo", dependencies=[Depends(require_permission("students.modify"))])
def upload_student_photo(student_id: int, file: UploadFile = File(...), crop_x: float | None = Form(default=None), crop_y: float | None = Form(default=None), crop_size: float | None = Form(default=None),
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Bouton "Importer une photo" de la grille élèves: dépose un fichier
    (jpg/png), normalise l'image (orientation, taille) et l'associe à
    l'élève."""
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")

    max_bytes = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
    raw = file.file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Photo trop volumineuse (max {settings.MAX_PHOTO_SIZE_MB} Mo)")
    # Le client peut fournir un recadrage carré en coordonnées de l'image source.
    # Le service applique de nouveau les limites et normalise en 600×600.
    if crop_x is not None or crop_y is not None or crop_size is not None:
        if crop_x is None or crop_y is None or crop_size is None or crop_size <= 0:
            raise HTTPException(status_code=400, detail="Paramètres de recadrage incomplets")
        try:
            from PIL import Image, ImageOps
            import io
            image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
            if crop_x < 0 or crop_y < 0 or crop_x + crop_size > image.width or crop_y + crop_size > image.height:
                raise HTTPException(status_code=422, detail="Zone de recadrage hors image")
            image = image.crop((int(crop_x), int(crop_y), int(crop_x + crop_size), int(crop_y + crop_size)))
            buf = io.BytesIO(); image.save(buf, "JPEG", quality=90, optimize=True); raw = buf.getvalue()
            file.filename = (file.filename or "photo.jpg").rsplit(".", 1)[0] + ".jpg"
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Recadrage impossible: {exc}") from exc
    relative_path = save_student_photo(student_id, file, raw)

    student.photo_path = relative_path
    db.commit()
    log_action(db, student.school_id, current_user, "student.photo.upload", "Student", student.id)
    return {"status": "ok", "photo_path": relative_path}


@router.get("/students/{student_id}/photo", dependencies=[Depends(require_permission("students.view"))])
def get_student_photo(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin) or not student.photo_path:
        raise HTTPException(status_code=404, detail="Aucune photo pour cet élève")
    path = resolve_media_path(student.photo_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier photo introuvable sur le serveur")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/students/{student_id}/photo", dependencies=[Depends(require_permission("students.modify"))])
def remove_student_photo(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    delete_student_photo(student_id)
    student.photo_path = None
    db.commit()
    log_action(db, student.school_id, current_user, "student.photo.remove", "Student", student.id)
    return {"status": "ok"}



# ---------- Dossier famille / inscriptions ----------

@router.get("/students/{student_id}/enrollment", dependencies=[Depends(require_permission("students.view"))])
def student_enrollment(student_id: int, academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    q = db.query(ClassMembership).filter(ClassMembership.student_id == student_id)
    if academic_year_id:
        q = q.filter(ClassMembership.academic_year_id == academic_year_id)
    memberships = q.order_by(ClassMembership.enrolled_at.desc()).all()
    return [{"id":m.id,"class_id":m.class_id,"class_name":m.school_class.name if m.school_class else None,"academic_year_id":m.academic_year_id,"enrolled_at":m.enrolled_at.isoformat(),"left_at":m.left_at.isoformat() if m.left_at else None,"enrollment_type":m.enrollment_type,"current":m.left_at is None} for m in memberships]


@router.post("/enrollments", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("students.transfer"))])
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, payload.student_id)
    school_class = db.get(SchoolClass, payload.class_id)
    if (not student or (student.school_id != current_user.school_id and not current_user.is_superadmin)
            or not school_class or school_class.school_id != student.school_id):
        raise HTTPException(status_code=400, detail="Élève ou classe invalide pour cet établissement")
    if school_class.academic_year_id != payload.academic_year_id:
        raise HTTPException(status_code=400, detail="La classe n'appartient pas à l'année scolaire sélectionnée")
    existing = db.query(ClassMembership).filter(ClassMembership.student_id==student.id, ClassMembership.academic_year_id==payload.academic_year_id, ClassMembership.left_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet élève possède déjà une inscription active pour cette année")
    active_count = db.query(ClassMembership).filter(ClassMembership.class_id == school_class.id, ClassMembership.left_at.is_(None)).count()
    if school_class.capacity is not None and active_count >= school_class.capacity:
        raise HTTPException(status_code=409, detail="La capacité de cette classe est atteinte")
    membership = ClassMembership(**payload.model_dump())
    db.add(membership); db.commit(); db.refresh(membership)
    log_action(db, student.school_id, current_user, "student.enrollment.create", "ClassMembership", membership.id, new_value=school_class.name)
    return {"id":membership.id,"status":"ok","class_id":membership.class_id,"class_name":school_class.name}


@router.post("/enrollments/transfer", dependencies=[Depends(require_permission("students.transfer"))])
def transfer_enrollment(payload: EnrollmentTransfer, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, payload.student_id); target = db.get(SchoolClass, payload.target_class_id)
    if not student or student.school_id != current_user.school_id or not target or target.school_id != current_user.school_id:
        raise HTTPException(status_code=400, detail="Élève ou classe cible invalide")
    if target.academic_year_id != payload.academic_year_id:
        raise HTTPException(status_code=400, detail="La classe cible n'appartient pas à l'année sélectionnée")
    current = db.query(ClassMembership).filter(ClassMembership.student_id==student.id, ClassMembership.academic_year_id==payload.academic_year_id, ClassMembership.left_at.is_(None)).first()
    if not current:
        raise HTTPException(status_code=404, detail="Aucune inscription active à transférer")
    if current.class_id == target.id:
        raise HTTPException(status_code=409, detail="L'élève est déjà dans cette classe")
    target_count = db.query(ClassMembership).filter(ClassMembership.class_id == target.id, ClassMembership.left_at.is_(None)).count()
    if target.capacity is not None and target_count >= target.capacity:
        raise HTTPException(status_code=409, detail="La capacité de la classe cible est atteinte")
    current.left_at = payload.effective_date
    new_m = ClassMembership(student_id=student.id,class_id=target.id,academic_year_id=payload.academic_year_id,enrolled_at=payload.effective_date,enrollment_type="mutation")
    db.add(new_m); db.commit(); db.refresh(new_m)
    log_action(db, student.school_id, current_user, "student.enrollment.transfer", "ClassMembership", new_m.id, old_value=str(current.class_id), new_value=f"{target.id}:{payload.reason or ''}")
    return {"status":"ok","from_class_id":current.class_id,"to_class_id":target.id,"membership_id":new_m.id}


@router.get("/students/{student_id}/guardians", response_model=list[GuardianOut], dependencies=[Depends(require_permission("students.view"))])
def list_student_guardians(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, student_id)
    if not student or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    return [link.guardian for link in student.guardian_links]


@router.post("/guardians", response_model=GuardianOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("students.modify"))])
def create_guardian(payload: GuardianCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Établissement non autorisé")
    guardian = Guardian(**payload.model_dump()); db.add(guardian); db.commit(); db.refresh(guardian)
    log_action(db, guardian.school_id, current_user, "guardian.create", "Guardian", guardian.id)
    return guardian


@router.post("/students/{student_id}/guardians/{guardian_id}", dependencies=[Depends(require_permission("students.modify"))])
def link_guardian(student_id: int, guardian_id: int, is_primary_contact: bool=False, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    student=db.get(Student,student_id); guardian=db.get(Guardian,guardian_id)
    if not student or student.school_id != current_user.school_id or not guardian or guardian.school_id != current_user.school_id:
        raise HTTPException(status_code=400, detail="Élève ou responsable invalide")
    if db.query(StudentGuardian).filter_by(student_id=student_id,guardian_id=guardian_id).first():
        raise HTTPException(status_code=409, detail="Ce responsable est déjà lié à l'élève")
    if is_primary_contact:
        for link in db.query(StudentGuardian).filter_by(student_id=student_id,is_primary_contact=True).all(): link.is_primary_contact=False
    link=StudentGuardian(student_id=student_id,guardian_id=guardian_id,is_primary_contact=is_primary_contact); db.add(link); db.commit()
    log_action(db,student.school_id,current_user,"guardian.link","StudentGuardian",link.id); return {"status":"ok"}


@router.patch("/guardians/{guardian_id}", response_model=GuardianOut, dependencies=[Depends(require_permission("students.modify"))])
def update_guardian(guardian_id:int,payload:GuardianUpdate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    guardian=db.get(Guardian,guardian_id)
    if not guardian or guardian.school_id != current_user.school_id: raise HTTPException(status_code=404,detail="Responsable introuvable")
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(guardian,k,v)
    db.commit(); db.refresh(guardian); log_action(db,guardian.school_id,current_user,"guardian.update","Guardian",guardian.id); return guardian

# ---------- Export / import Excel & PDF ----------

@router.get("/students/export.xlsx", dependencies=[Depends(require_permission("students.export"))])
def export_students_excel(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    students = db.query(Student).filter(Student.school_id == school_id, Student.is_active.is_(True)).order_by(
        Student.last_name, Student.first_name
    ).all()
    rows = [
        {
            "matricule": s.matricule, "first_name": s.first_name, "last_name": s.last_name,
            "birth_date": s.birth_date, "sex": s.sex, "nationality": s.nationality,
            "status": s.status, "class_name": _current_class_name(db, s.id),
        }
        for s in students
    ]
    content = export_students_xlsx(rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=eleves.xlsx"},
    )


@router.get("/students/export.pdf", dependencies=[Depends(require_permission("students.export"))])
def export_students_pdf(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    from app.models.organization import School

    school = db.get(School, school_id)
    students = db.query(Student).filter(Student.school_id == school_id, Student.is_active.is_(True)).order_by(
        Student.last_name, Student.first_name
    ).all()
    rows = [
        {
            "matricule": s.matricule, "first_name": s.first_name, "last_name": s.last_name,
            "sex": s.sex, "status": s.status, "class_name": _current_class_name(db, s.id),
        }
        for s in students
    ]
    content = generate_students_list_pdf(school.name if school else "SIGMA", rows)
    return Response(
        content=content, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=liste_eleves.pdf"},
    )


@router.get("/students/import/template.xlsx")
def download_import_template():
    """Gabarit vierge à distribuer au secrétariat pour une saisie en masse
    (§21 du cahier des charges: 'import Excel')."""
    content = build_student_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modele_import_eleves.xlsx"},
    )


@router.post("/students/import", dependencies=[Depends(require_permission("students.import"))])
def import_students_excel(school_id: int, file: UploadFile = File(...),
                           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Import en masse depuis un classeur Excel (gabarit disponible via
    GET /api/students/import/template.xlsx). `school_id` est passé en
    paramètre de requête (ex: /api/students/import?school_id=1), le fichier
    en multipart/form-data (champ "file") — c'est ce qu'envoie la grille
    élèves (`static/students.html`).
    Chaque ligne est validée indépendamment: une ligne invalide est
    rapportée mais ne bloque pas l'import des autres.
    """
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    max_bytes = settings.MAX_IMPORT_UPLOAD_BYTES
    raw = file.file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Fichier d’import trop volumineux")
    try:
        rows = parse_students_import(raw)
    except StudentImportRowError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Un import massif ne doit jamais contourner les quotas du forfait.
    # On réserve la capacité uniquement pour les nouvelles lignes qui seront
    # effectivement créées; les doublons sont exclus du calcul.
    new_rows = []
    skipped, errors = 0, []
    for row in rows:
        row_number = row.get("_row_number")
        matricule = row.get("matricule")
        exists = db.query(Student).filter(
            Student.school_id == school_id, Student.matricule == matricule
        ).first()
        if exists:
            skipped += 1
            errors.append({"row": row_number, "reason": f"Matricule {matricule} déjà existant, ligne ignorée"})
            continue
        new_rows.append(row)

    try:
        state = enforce_subscription_capacity(db, school_id, "students")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    available = state["limit"] - state["current"]
    if len(new_rows) > available:
        raise HTTPException(
            status_code=403,
            detail=f"Import refusé: {len(new_rows)} nouveaux élèves, mais seulement {available} place(s) restante(s) sur le plan {state['plan']}",
        )

    created = 0
    for row in new_rows:
        row.pop("_row_number", None)
        student = Student(school_id=school_id, **row)
        db.add(student)
        created += 1
        row_number = row.pop("_row_number")
        exists = db.query(Student).filter(
            Student.school_id == school_id, Student.matricule == row["matricule"]
        ).first()
        if exists:
            skipped += 1
            errors.append({"row": row_number, "reason": f"Matricule {row['matricule']} déjà existant, ligne ignorée"})
            continue

        student = Student(school_id=school_id, **row)
        db.add(student)
        created += 1

    db.commit()
    log_action(db, school_id, current_user, "student.import", "Student",
               new_value=f"{created} créé(s), {skipped} ignoré(s)")
    return {"created": created, "skipped": skipped, "errors": errors}


# ---------- Classes ----------

@router.post("/classes", response_model=SchoolClassOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.classes.create"))])
def create_class(payload: SchoolClassCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Établissement non autorisé")
    level = db.get(Level, payload.level_id)
    if not level or level.school_id != payload.school_id:
        raise HTTPException(status_code=400, detail="Niveau invalide pour cet établissement")
    if payload.stream_id:
        stream = db.get(Stream, payload.stream_id)
        if not stream or stream.school_id != payload.school_id:
            raise HTTPException(status_code=400, detail="Section / série invalide pour cet établissement")
    year = db.get(__import__('app.models.organization', fromlist=['AcademicYear']).AcademicYear, payload.academic_year_id)
    if not year or year.school_id != payload.school_id:
        raise HTTPException(status_code=400, detail="Année scolaire invalide")
    school_class = SchoolClass(**payload.model_dump())
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    log_action(db, payload.school_id, current_user, "class.create", "SchoolClass", school_class.id, new_value=payload.name)
    return school_class


@router.patch("/classes/{class_id}", response_model=SchoolClassOut,
              dependencies=[Depends(require_permission("administration.classes.create"))])
def update_class(class_id: int, payload: SchoolClassUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_class = db.get(SchoolClass, class_id)
    if school_class is None or (school_class.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Classe introuvable")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return school_class
    school_id = school_class.school_id
    if "level_id" in changes and changes["level_id"] is not None:
        level = db.get(Level, changes["level_id"])
        if not level or level.school_id != school_id or not level.is_active:
            raise HTTPException(status_code=400, detail="Niveau invalide pour cet établissement")
    if "stream_id" in changes and changes["stream_id"] is not None:
        stream = db.get(Stream, changes["stream_id"])
        if not stream or stream.school_id != school_id or not stream.is_active:
            raise HTTPException(status_code=400, detail="Série invalide pour cet établissement")
    if "academic_year_id" in changes and changes["academic_year_id"] is not None:
        from app.models.organization import AcademicYear
        year = db.get(AcademicYear, changes["academic_year_id"])
        if not year or year.school_id != school_id or year.is_archived:
            raise HTTPException(status_code=400, detail="Année scolaire invalide ou archivée")
        if changes["academic_year_id"] != school_class.academic_year_id:
            membership_count = db.query(ClassMembership).filter(ClassMembership.class_id == class_id).count()
            if membership_count:
                raise HTTPException(status_code=409, detail="Cette classe possède un historique d'inscriptions : son année scolaire ne peut pas être changée. Créez une nouvelle classe pour une autre année.")
    if "campus_id" in changes and changes["campus_id"] is not None:
        from app.models.organization import Campus
        campus = db.get(Campus, changes["campus_id"])
        if not campus or campus.school_id != school_id or not campus.is_active:
            raise HTTPException(status_code=400, detail="Campus invalide pour cet établissement")
    if "homeroom_teacher_id" in changes and changes["homeroom_teacher_id"] is not None:
        teacher = db.get(User, changes["homeroom_teacher_id"])
        if not teacher or teacher.school_id != school_id or not teacher.is_active:
            raise HTTPException(status_code=400, detail="Enseignant invalide pour cet établissement")
    if "capacity" in changes and changes["capacity"] is not None and changes["capacity"] < 1:
        raise HTTPException(status_code=400, detail="La capacité doit être supérieure à zéro")
    if "name" in changes and changes["name"] is not None and not changes["name"].strip():
        raise HTTPException(status_code=400, detail="Le nom de la classe ne peut pas être vide")
    old_value = f"name={school_class.name};level_id={school_class.level_id};stream_id={school_class.stream_id};year_id={school_class.academic_year_id};capacity={school_class.capacity}"
    for key, value in changes.items():
        setattr(school_class, key, value.strip() if key == "name" and isinstance(value, str) else value)
    db.commit(); db.refresh(school_class)
    new_value = f"name={school_class.name};level_id={school_class.level_id};stream_id={school_class.stream_id};year_id={school_class.academic_year_id};capacity={school_class.capacity}"
    log_action(db, school_id, current_user, "class.update", "SchoolClass", school_class.id, old_value=old_value, new_value=new_value)
    return school_class


@router.get("/classes/{class_id}/edit-context", dependencies=[Depends(require_permission("students.view"))])
def class_edit_context(class_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    school_class=db.get(SchoolClass,class_id)
    if not school_class or (school_class.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Classe introuvable")
    return {"id":school_class.id,"name":school_class.name,"academic_year_id":school_class.academic_year_id,"level_id":school_class.level_id,"stream_id":school_class.stream_id,"capacity":school_class.capacity,"is_active":school_class.is_active}


@router.delete("/classes/{class_id}", dependencies=[Depends(require_permission("administration.classes.create"))])
def deactivate_class(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_class = db.get(SchoolClass, class_id)
    if school_class is None or (school_class.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Classe introuvable")
    active_members = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)).count()
    if active_members:
        raise HTTPException(status_code=409, detail=f"Impossible de supprimer cette classe : {active_members} élève(s) y sont encore affecté(s). Transférez-les d'abord.")
    school_class.is_active = False
    db.commit()
    log_action(db, school_class.school_id, current_user, "class.deactivate", "SchoolClass", school_class.id, old_value=school_class.name, new_value="inactive")
    return {"status": "ok", "id": school_class.id, "is_active": False}


@router.post("/classes/{class_id}/restore", dependencies=[Depends(require_permission("administration.classes.create"))])
def restore_class(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_class = db.get(SchoolClass, class_id)
    if school_class is None or (school_class.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Classe introuvable")
    school_class.is_active = True
    db.commit()
    log_action(db, school_class.school_id, current_user, "class.restore", "SchoolClass", school_class.id, new_value=school_class.name)
    return {"status": "ok", "id": school_class.id, "is_active": True}


@router.get("/classes", response_model=list[SchoolClassOut], dependencies=[Depends(require_permission("students.view"))])
def list_classes(school_id: int, academic_year_id: int | None = None, include_inactive: bool = False, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    query = db.query(SchoolClass).filter(SchoolClass.school_id == school_id)
    if not include_inactive:
        query = query.filter(SchoolClass.is_active.is_(True))
    if academic_year_id:
        query = query.filter(SchoolClass.academic_year_id == academic_year_id)
    return query.order_by(SchoolClass.name).all()


@router.get("/classes/{class_id}/students", response_model=list[StudentOut], dependencies=[Depends(require_permission("students.view"))])
def list_class_students(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_class = db.get(SchoolClass, class_id)
    if school_class is None or (school_class.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Classe introuvable")
    memberships = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.left_at.is_(None)).all()
    students = [db.get(Student, m.student_id) for m in memberships]
    return students


# ---------- Tuteurs / responsables ----------

@router.post("/student-guardians", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("students.modify"))])
def link_guardian(payload: StudentGuardianLink, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.get(Student, payload.student_id)
    guardian = db.get(Guardian, payload.guardian_id)
    if not student or not guardian or student.school_id != guardian.school_id:
        raise HTTPException(status_code=404, detail="Élève ou responsable introuvable")
    if student.school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    link = StudentGuardian(**payload.model_dump())
    db.add(link)
    db.commit()
    return {"status": "ok"}


# ---------- Niveaux / séries (configuration) ----------

@router.post("/levels", dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_level(school_id: int, name: str, order_index: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin: raise HTTPException(status_code=403, detail="Accès refusé")
    level = Level(school_id=school_id, name=name, order_index=order_index)
    db.add(level)
    db.commit()
    db.refresh(level)
    return {"id": level.id, "name": level.name}


@router.patch("/levels/{level_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def update_level(level_id: int, payload: LevelUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    level = db.get(Level, level_id)
    if not level or (level.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"id": level.id, "name": level.name, "order_index": level.order_index}
    if "name" in changes and (changes["name"] is None or not changes["name"].strip()):
        raise HTTPException(status_code=400, detail="Le nom du niveau ne peut pas être vide")
    if "order_index" in changes and (changes["order_index"] is None or changes["order_index"] < 1):
        raise HTTPException(status_code=400, detail="L'ordre doit être supérieur ou égal à 1")
    old_value = f"name={level.name};order_index={level.order_index}"
    if "name" in changes: level.name = changes["name"].strip()
    if "order_index" in changes: level.order_index = changes["order_index"]
    db.commit(); db.refresh(level)
    log_action(db, level.school_id, current_user, "level.update", "Level", level.id, old_value=old_value, new_value=f"name={level.name};order_index={level.order_index}")
    return {"id": level.id, "name": level.name, "order_index": level.order_index}


@router.delete("/levels/{level_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def deactivate_level(level_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    level = db.get(Level, level_id)
    if not level or (level.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    active_classes = db.query(SchoolClass).filter(SchoolClass.level_id == level_id, SchoolClass.is_active.is_(True)).count()
    if active_classes:
        raise HTTPException(status_code=409, detail=f"Impossible de supprimer ce niveau : {active_classes} classe(s) l'utilisent encore. Modifiez ou désactivez d'abord ces classes.")
    level.is_active = False
    db.commit(); log_action(db, level.school_id, current_user, "level.deactivate", "Level", level.id, old_value=level.name, new_value="inactive")
    return {"status":"ok","id":level.id,"is_active":False}


@router.post("/levels/{level_id}/restore", dependencies=[Depends(require_permission("administration.settings.modify"))])
def restore_level(level_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    level=db.get(Level,level_id)
    if not level or (level.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404, detail="Niveau introuvable")
    level.is_active=True; db.commit(); log_action(db,level.school_id,current_user,"level.restore","Level",level.id,new_value=level.name)
    return {"status":"ok","id":level.id,"is_active":True}


@router.get("/levels", dependencies=[Depends(require_permission("students.view"))])
def list_levels(school_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin: raise HTTPException(status_code=403, detail="Accès refusé")
    q = db.query(Level).filter(Level.school_id == school_id)
    if not include_inactive: q = q.filter(Level.is_active.is_(True))
    levels = q.order_by(Level.order_index).all()
    return [{"id": l.id, "name": l.name, "order_index": l.order_index, "is_active": l.is_active} for l in levels]


@router.post("/streams", dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_stream(school_id: int, name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin: raise HTTPException(status_code=403, detail="Accès refusé")
    stream = Stream(school_id=school_id, name=name)
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return {"id": stream.id, "name": stream.name}


@router.patch("/streams/{stream_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def update_stream(stream_id:int, payload:StreamUpdate, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    stream=db.get(Stream,stream_id)
    if not stream or (stream.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404, detail="Série introuvable")
    changes=payload.model_dump(exclude_unset=True)
    if "name" in changes and (changes["name"] is None or not changes["name"].strip()): raise HTTPException(status_code=400,detail="Le nom de la série ne peut pas être vide")
    old=stream.name
    if "name" in changes: stream.name=changes["name"].strip()
    db.commit(); db.refresh(stream); log_action(db,stream.school_id,current_user,"stream.update","Stream",stream.id,old_value=old,new_value=stream.name)
    return {"id":stream.id,"name":stream.name}


@router.delete("/streams/{stream_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def deactivate_stream(stream_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    stream=db.get(Stream,stream_id)
    if not stream or (stream.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Série introuvable")
    active_classes=db.query(SchoolClass).filter(SchoolClass.stream_id==stream_id,SchoolClass.is_active.is_(True)).count()
    if active_classes: raise HTTPException(status_code=409,detail=f"Impossible de supprimer cette série : {active_classes} classe(s) l'utilisent encore.")
    stream.is_active=False; db.commit(); log_action(db,stream.school_id,current_user,"stream.deactivate","Stream",stream.id,old_value=stream.name,new_value="inactive")
    return {"status":"ok","id":stream.id,"is_active":False}


@router.post("/streams/{stream_id}/restore", dependencies=[Depends(require_permission("administration.settings.modify"))])
def restore_stream(stream_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    stream=db.get(Stream,stream_id)
    if not stream or (stream.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Série introuvable")
    stream.is_active=True; db.commit(); log_action(db,stream.school_id,current_user,"stream.restore","Stream",stream.id,new_value=stream.name)
    return {"status":"ok","id":stream.id,"is_active":True}


@router.get("/streams", dependencies=[Depends(require_permission("students.view"))])
def list_streams(school_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin: raise HTTPException(status_code=403, detail="Accès refusé")
    q = db.query(Stream).filter(Stream.school_id == school_id)
    if not include_inactive: q = q.filter(Stream.is_active.is_(True))
    streams = q.order_by(Stream.name).all()
    return [{"id": s.id, "name": s.name, "is_active": s.is_active} for s in streams]


@router.get("/guardians", dependencies=[Depends(require_permission("students.view"))])
def list_guardians(school_id: int, search: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin: raise HTTPException(status_code=403, detail="Accès refusé")
    q=db.query(Guardian).filter(Guardian.school_id==school_id, Guardian.is_active.is_(True))
    if search:
        like=f"%{search}%"; q=q.filter((Guardian.first_name.ilike(like)) | (Guardian.last_name.ilike(like)) | (Guardian.phone.ilike(like)))
    return [{"id":g.id,"name":f"{g.first_name} {g.last_name}","relationship_type":g.relationship_type,"phone":g.phone} for g in q.order_by(Guardian.last_name,Guardian.first_name).all()]
