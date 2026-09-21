from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.deps import get_current_user, require_permission, assert_school_access
from app.models.security import User, UserPost
from app.models.academic import Subject, TeacherAssignment, Assessment, Grade, GradeAudit, ReportCard, GRADE_STATES
from app.models.evaluation import EvaluationPeriodClosure
from app.models.sync import SyncEntityVersion
from app.schemas.academic import (
    SubjectCreate, SubjectOut, TeacherAssignmentCreate, AssessmentCreate, AssessmentOut,
    GradeUpsert, GradeOut, GradeStateTransition, GeneralAverageOut,
)
from app.services.audit import log_action
from app.services.grading_engine import compute_general_average, compute_class_ranking
from app.services.pdf_engine import generate_report_card_pdf, generate_report_cards_batch_pdf
from app.services.evaluation_engine import transition_state

router = APIRouter(prefix="/api", tags=["Académique"])

def _class_access(db, current_user, class_id):
    from app.models.students import SchoolClass
    cls = db.get(SchoolClass, class_id)
    if cls is None or (cls.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Classe introuvable")
    return cls

def _period_access(db, current_user, period_id):
    from app.models.organization import AcademicPeriod, AcademicYear
    period = db.get(AcademicPeriod, period_id)
    year = db.get(AcademicYear, period.academic_year_id) if period else None
    if period is None or year is None or (year.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Période scolaire introuvable")
    return period

def _teacher_academic_guard(db, current_user, class_id: int, academic_year_id: int, subject_id: int | None = None):
    """Borne les opérations académiques aux affectations réelles de l'enseignant."""
    if current_user.is_superadmin:
        return
    from app.services.authorization import user_has_permission
    if any(user_has_permission(db, current_user, code, {}) for code in (
        "administration.settings.modify", "administration.users.modify", "academic.report_cards.publish"
    )):
        return
    q = db.query(TeacherAssignment).filter(
        TeacherAssignment.teacher_id == current_user.id,
        TeacherAssignment.class_id == class_id,
        TeacherAssignment.academic_year_id == academic_year_id,
    )
    if subject_id is not None:
        q = q.filter(TeacherAssignment.subject_id == subject_id)
    if q.first() is None:
        raise HTTPException(status_code=403, detail="Classe/matière non affectée à cet enseignant")


def _report_card_access(db, current_user, report_card_id):
    report_card = db.get(ReportCard, report_card_id)
    if report_card is None:
        raise HTTPException(status_code=404, detail="Bulletin introuvable")
    _class_access(db, current_user, report_card.class_id)
    _period_access(db, current_user, report_card.academic_period_id)
    return report_card


# ---------- Matières ----------

@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.patch("/subjects/{subject_id}", response_model=SubjectOut,
              dependencies=[Depends(require_permission("administration.settings.modify"))])
def update_subject(subject_id:int, payload:dict, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    subject=db.get(Subject,subject_id)
    if not subject or (subject.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Matière introuvable")
    allowed={k:v for k,v in payload.items() if k in {"name","default_coefficient"}}
    if "name" in allowed and (not isinstance(allowed["name"],str) or not allowed["name"].strip()): raise HTTPException(status_code=400,detail="Le nom de la matière ne peut pas être vide")
    if "default_coefficient" in allowed and float(allowed["default_coefficient"]) <= 0: raise HTTPException(status_code=400,detail="Le coefficient doit être supérieur à zéro")
    old=f"name={subject.name};coefficient={subject.default_coefficient}"
    for k,v in allowed.items(): setattr(subject,k,v.strip() if k=="name" else v)
    db.commit(); db.refresh(subject); log_action(db,subject.school_id,current_user,"subject.update","Subject",subject.id,old_value=old,new_value=f"name={subject.name};coefficient={subject.default_coefficient}")
    return subject


@router.delete("/subjects/{subject_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def deactivate_subject(subject_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    subject=db.get(Subject,subject_id)
    if not subject or (subject.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Matière introuvable")
    subject.is_active=False; db.commit(); log_action(db,subject.school_id,current_user,"subject.deactivate","Subject",subject.id,old_value=subject.name,new_value="inactive")
    return {"status":"ok","id":subject.id,"is_active":False}


@router.post("/subjects/{subject_id}/restore", dependencies=[Depends(require_permission("administration.settings.modify"))])
def restore_subject(subject_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    subject=db.get(Subject,subject_id)
    if not subject or (subject.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(status_code=404,detail="Matière introuvable")
    subject.is_active=True; db.commit(); log_action(db,subject.school_id,current_user,"subject.restore","Subject",subject.id,new_value=subject.name)
    return {"status":"ok","id":subject.id,"is_active":True}


@router.get("/subjects", response_model=list[SubjectOut], dependencies=[Depends(require_permission("academic.assessments.view"))])
def list_subjects(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return db.query(Subject).filter(Subject.school_id == school_id, Subject.is_active.is_(True)).order_by(Subject.name).all()


# ---------- Affectations enseignants ----------

@router.post("/teacher-assignments", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.settings.modify"))])
def assign_teacher(payload: TeacherAssignmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import SchoolClass
    from app.models.organization import AcademicYear, School
    school_class = db.get(SchoolClass, payload.class_id)
    subject = db.get(Subject, payload.subject_id)
    teacher = db.get(User, payload.teacher_id)
    year = db.get(AcademicYear, payload.academic_year_id)
    if not school_class or not subject or not teacher or not year:
        raise HTTPException(status_code=400, detail="Affectation invalide: classe, matière, enseignant ou année introuvable")
    if school_class.school_id != current_user.school_id or subject.school_id != current_user.school_id or teacher.school_id != current_user.school_id or year.school_id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Les ressources doivent appartenir au même établissement")
    assignment = TeacherAssignment(**payload.model_dump())
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette affectation enseignant/matière/classe existe déjà")
    db.refresh(assignment)
    log_action(db, current_user.school_id, current_user, "teacher_assignment.create", "TeacherAssignment", assignment.id)
    return {"status": "ok", "assignment_id": assignment.id}


@router.get("/teachers", dependencies=[Depends(require_permission("academic.assessments.view"))])
def list_teachers(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).order_by(User.last_name, User.first_name).all()
    return [{"id": u.id, "name": f"{u.first_name} {u.last_name}", "username": u.username} for u in users]


@router.get("/teacher-assignments", dependencies=[Depends(require_permission("academic.assessments.view"))])
def list_teacher_assignments(academic_year_id: int, class_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import SchoolClass
    from app.models.organization import AcademicYear
    year = db.get(AcademicYear, academic_year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="Année scolaire introuvable")
    assert_school_access(current_user, year.school_id)
    if class_id:
        cls = db.get(SchoolClass, class_id)
        if cls is None or cls.school_id != year.school_id:
            raise HTTPException(status_code=404, detail="Classe introuvable")
    q = db.query(TeacherAssignment).filter(TeacherAssignment.academic_year_id == academic_year_id)
    if class_id:
        q = q.filter(TeacherAssignment.class_id == class_id)
    assignments = q.order_by(TeacherAssignment.class_id, TeacherAssignment.subject_id).all()
    teacher_ids = {a.teacher_id for a in assignments}
    subject_ids = {a.subject_id for a in assignments}
    teachers = {u.id: u for u in db.query(User).filter(User.id.in_(teacher_ids)).all()} if teacher_ids else {}
    subjects = {s.id: s for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()} if subject_ids else {}
    rows = []
    for a in assignments:
        teacher = teachers.get(a.teacher_id)
        subject = subjects.get(a.subject_id)
        if teacher and subject:
            rows.append({"id": a.id, "teacher_id": a.teacher_id, "teacher_name": f"{teacher.first_name} {teacher.last_name}", "subject_id": a.subject_id, "subject_name": subject.name, "class_id": a.class_id, "coefficient": a.coefficient, "weekly_hours": a.weekly_hours})
    return rows


# ---------- Évaluations ----------

@router.post("/assessments", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("academic.assessments.create"))])
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Un enseignant ne peut créer une évaluation que sur ses propres
    classes/matières: vérifié via la permission académique scopée.
    """
    from app.services.authorization import require_permission as check_permission, PermissionDenied

    cls = _class_access(db, current_user, payload.class_id)
    period = _period_access(db, current_user, payload.academic_period_id)
    subject = db.get(Subject, payload.subject_id)
    if subject is None or (subject.school_id != cls.school_id):
        raise HTTPException(status_code=404, detail="Matière introuvable")
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")

    try:
        check_permission(
            db, current_user, "academic.grades.create",
            context={"subject_id": payload.subject_id, "class_id": payload.class_id},
        )
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    assessment = Assessment(**payload.model_dump(), created_by_id=current_user.id)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/assessments", response_model=list[AssessmentOut], dependencies=[Depends(require_permission("academic.assessments.view"))])
def list_assessments(class_id: int, academic_period_id: int | None = None, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    cls = _class_access(db, current_user, class_id)
    if academic_period_id is not None:
        period = _period_access(db, current_user, academic_period_id)
        if period.academic_year_id != cls.academic_year_id:
            raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    from app.services.authorization import user_has_permission
    if not any(user_has_permission(db, current_user, code, {"class_id": cls.id}) for code in ("academic.grades.view", "academic.grades.enter")):
        raise HTTPException(status_code=403, detail="Permission académique insuffisante")
    query = db.query(Assessment).filter(Assessment.class_id == class_id, Assessment.is_active.is_(True))
    if academic_period_id:
        query = query.filter(Assessment.academic_period_id == academic_period_id)
    rows = query.all()
    if not current_user.is_superadmin and not any(user_has_permission(db, current_user, code, {}) for code in ("administration.settings.modify", "administration.users.modify", "academic.report_cards.publish")):
        assigned_subjects = {a.subject_id for a in db.query(TeacherAssignment).filter(
            TeacherAssignment.teacher_id == current_user.id, TeacherAssignment.class_id == cls.id,
            TeacherAssignment.academic_year_id == cls.academic_year_id).all()}
        rows = [a for a in rows if a.subject_id in assigned_subjects]
    return rows


# ---------- Notes ----------

@router.get("/assessments/{assessment_id}/grades", dependencies=[Depends(require_permission("academic.grades.view"))])
def list_assessment_grades(assessment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import Student, ClassMembership
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Évaluation introuvable")
    cls = _class_access(db, current_user, assessment.class_id)
    period = _period_access(db, current_user, assessment.academic_period_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    from app.services.authorization import user_has_permission
    if not any(user_has_permission(db, current_user, code, {"class_id": cls.id, "subject_id": assessment.subject_id}) for code in ("academic.grades.view", "academic.grades.enter")):
        raise HTTPException(status_code=403, detail="Permission académique insuffisante")
    _teacher_academic_guard(db, current_user, cls.id, cls.academic_year_id, assessment.subject_id)

    memberships = db.query(ClassMembership.student_id).filter(
        ClassMembership.academic_year_id == cls.academic_year_id,
        ClassMembership.class_id == assessment.class_id, ClassMembership.left_at.is_(None)
    ).all()
    student_ids = [row[0] for row in memberships]
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    grades = {g.student_id: g for g in db.query(Grade).filter(Grade.assessment_id == assessment_id, Grade.student_id.in_(student_ids)).all()} if student_ids else {}
    grade_ids = [g.id for g in grades.values()]
    versions = {}
    if grade_ids:
        versions = {str(v.entity_id): v.version for v in db.query(SyncEntityVersion).filter(
            SyncEntityVersion.school_id == current_user.school_id,
            SyncEntityVersion.entity_type == "grade",
            SyncEntityVersion.entity_id.in_([str(x) for x in grade_ids]),
        ).all()}
    rows = []
    for student_id in student_ids:
        student = students.get(student_id)
        grade = grades.get(student_id)
        rows.append({
            "student_id": student_id,
            "student_name": f"{student.first_name} {student.last_name}" if student else "—",
            "matricule": student.matricule if student else "—",
            "grade_id": grade.id if grade else None,
            "score": grade.score if grade else None,
            "is_absent": grade.is_absent if grade else False,
            "state": grade.state if grade else "draft",
            "sync_version": versions.get(str(grade.id), 0) if grade else 0,
        })
    rows.sort(key=lambda r: r["student_name"])
    return rows


@router.post("/assessments/{assessment_id}/grades", response_model=list[GradeOut], dependencies=[Depends(require_permission("academic.grades.enter"))])
def upsert_grades(assessment_id: int, payload: list[GradeUpsert], db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """Saisie/mise à jour en masse des notes d'une évaluation (état: draft)."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Évaluation introuvable")
    _class_access(db, current_user, assessment.class_id)

    from app.services.authorization import require_permission as check_permission, PermissionDenied
    try:
        check_permission(
            db, current_user, "academic.grades.enter",
            context={"subject_id": assessment.subject_id, "class_id": assessment.class_id},
        )
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    from app.models.students import Student, ClassMembership
    member_ids = {row.student_id for row in db.query(ClassMembership.student_id).filter(
        ClassMembership.class_id == assessment.class_id,
        ClassMembership.academic_year_id == _class_access(db, current_user, assessment.class_id).academic_year_id,
        ClassMembership.left_at.is_(None),
    ).all()}

    student_ids = [item.student_id for item in payload]
    if len(student_ids) != len(set(student_ids)):
        raise HTTPException(status_code=422, detail="Un même élève ne peut apparaître qu'une fois dans un lot de notes")
    students = {
        student.id: student
        for student in db.query(Student).filter(
            Student.id.in_(student_ids),
            Student.school_id == current_user.school_id,
        ).all()
    } if student_ids else {}
    for student_id in student_ids:
        if student_id not in students or student_id not in member_ids:
            raise HTTPException(status_code=404, detail=f"Élève {student_id} introuvable dans cette classe")

    grades = db.query(Grade).filter(
        Grade.assessment_id == assessment_id,
        Grade.student_id.in_(student_ids),
    ).all() if student_ids else []
    grades_by_student = {grade.student_id: grade for grade in grades}
    results = []
    for item in payload:
        grade = grades_by_student.get(item.student_id)
        if grade is None:
            grade = Grade(assessment_id=assessment_id, student_id=item.student_id, state="draft")
            db.add(grade)
            grades_by_student[item.student_id] = grade
        if grade.state == "locked":
            raise HTTPException(status_code=409, detail=f"Note verrouillée pour l'élève {item.student_id}: modification interdite sans autorisation")
        grade.score = item.score
        grade.is_absent = item.is_absent
        grade.comment = item.comment
        results.append(grade)

    db.flush()
    grade_ids = [grade.id for grade in results]
    versions = db.query(SyncEntityVersion).filter(
        SyncEntityVersion.school_id == current_user.school_id,
        SyncEntityVersion.entity_type == "grade",
        SyncEntityVersion.entity_id.in_([str(grade_id) for grade_id in grade_ids]),
    ).all() if grade_ids else []
    versions_by_entity = {version.entity_id: version for version in versions}
    for grade in results:
        version = versions_by_entity.get(str(grade.id))
        if version is None:
            db.add(SyncEntityVersion(
                school_id=current_user.school_id, entity_type="grade",
                entity_id=str(grade.id), version=1,
            ))
        else:
            version.version += 1

    db.commit()
    for grade in results:
        db.refresh(grade)
    return results


@router.post("/grades/transition")
def transition_grades(payload: GradeStateTransition, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fait avancer un lot de notes selon le circuit séquentiel et protège les périodes clôturées."""
    if payload.to_state not in GRADE_STATES:
        raise HTTPException(status_code=400, detail=f"État inconnu. États valides: {GRADE_STATES}")
    required_permission = "academic.grades.lock" if payload.to_state == "locked" else "academic.report_cards.publish" if payload.to_state == "published" else "academic.grades.validate"
    from app.services.authorization import user_has_permission
    if not current_user.is_superadmin and not user_has_permission(db, current_user, required_permission, {}):
        raise HTTPException(status_code=403, detail="Permission insuffisante pour cette transition")

    updated = 0
    for grade_id in payload.grade_ids:
        grade = db.get(Grade, grade_id)
        if grade is None:
            continue
        assessment = db.get(Assessment, grade.assessment_id)
        if assessment is None:
            raise HTTPException(status_code=422, detail=f"Évaluation introuvable pour la note {grade.id}")
        from app.models.students import SchoolClass
        school_class = db.query(SchoolClass).filter(
            SchoolClass.id == assessment.class_id,
            SchoolClass.school_id == current_user.school_id,
        ).first() if not current_user.is_superadmin else db.get(SchoolClass, assessment.class_id)
        if school_class is None:
            raise HTTPException(status_code=403, detail="La note n'appartient pas à cet établissement")
        period = _period_access(db, current_user, assessment.academic_period_id)
        if period.academic_year_id != school_class.academic_year_id:
            raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
        _teacher_academic_guard(db, current_user, school_class.id, school_class.academic_year_id, assessment.subject_id)
        closure = db.query(EvaluationPeriodClosure).filter(
            EvaluationPeriodClosure.class_id == assessment.class_id,
            EvaluationPeriodClosure.academic_period_id == assessment.academic_period_id,
        ).first()
        if closure is not None and closure.status in {"closed", "published"}:
            raise HTTPException(status_code=409, detail="Période clôturée/publiée: transition de note interdite")
        if not transition_state(grade.state, payload.to_state):
            raise HTTPException(status_code=409, detail=f"Transition interdite: {grade.state} -> {payload.to_state}")
        history = GradeAudit(
            grade_id=grade.id, changed_by_id=current_user.id,
            from_state=grade.state, to_state=payload.to_state,
            old_score=grade.score, new_score=grade.score,
        )
        db.add(history)
        grade.state = payload.to_state
        version = db.query(SyncEntityVersion).filter(
            SyncEntityVersion.school_id == current_user.school_id,
            SyncEntityVersion.entity_type == "grade",
            SyncEntityVersion.entity_id == str(grade.id),
        ).first()
        if version is None:
            db.add(SyncEntityVersion(
                school_id=current_user.school_id, entity_type="grade",
                entity_id=str(grade.id), version=1,
            ))
        else:
            version.version += 1
        updated += 1

    db.commit()
    log_action(db, current_user.school_id, current_user, "grades.transition", "Grade",
               new_value=f"{updated} notes -> {payload.to_state}")
    return {"status": "ok", "updated": updated}


# ---------- Moyennes et classements ----------

@router.get("/students/{student_id}/average", response_model=GeneralAverageOut, dependencies=[Depends(require_permission("academic.grades.view"))])
def get_student_average(student_id: int, class_id: int, academic_period_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    from app.models.students import Student
    student = db.get(Student, student_id)
    cls = _class_access(db, current_user, class_id)
    period = _period_access(db, current_user, academic_period_id)
    if student is None or (student.school_id != cls.school_id):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    general_average, subjects = compute_general_average(db, student_id, class_id, academic_period_id)
    return GeneralAverageOut(
        student_id=student_id, class_id=class_id, academic_period_id=academic_period_id,
        general_average=general_average,
        subjects=[{"subject_id": s.subject_id, "subject_name": s.subject_name, "average": s.average, "coefficient": s.coefficient} for s in subjects],
    )


@router.get("/classes/{class_id}/ranking", dependencies=[Depends(require_permission("academic.grades.view"))])
def get_class_ranking(class_id: int, academic_period_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    cls = _class_access(db, current_user, class_id)
    period = _period_access(db, current_user, academic_period_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    ranking = compute_class_ranking(db, class_id, academic_period_id)
    return [{"rank": i + 1, "student_id": student_id, "average": avg} for i, (student_id, avg) in enumerate(ranking)]


# ---------- Bulletins ----------

@router.post("/report-cards/generate", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def generate_report_cards(class_id: int, academic_period_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Génère (ou régénère) les bulletins de toute une classe pour une période."""
    cls = _class_access(db, current_user, class_id)
    period = _period_access(db, current_user, academic_period_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    ranking = compute_class_ranking(db, class_id, academic_period_id)
    class_size = len(ranking)

    student_ids = [student_id for student_id, _ in ranking]
    existing = {rc.student_id: rc for rc in db.query(ReportCard).filter(
        ReportCard.student_id.in_(student_ids),
        ReportCard.academic_period_id == academic_period_id,
    ).all()} if student_ids else {}
    created_or_updated = 0
    for rank, (student_id, average) in enumerate(ranking, start=1):
        report_card = existing.get(student_id)
        if report_card is None:
            report_card = ReportCard(student_id=student_id, class_id=class_id, academic_period_id=academic_period_id)
            db.add(report_card)
        report_card.general_average = average
        report_card.class_rank = rank
        report_card.class_size = class_size
        created_or_updated += 1

    db.commit()
    log_action(db, current_user.school_id, current_user, "report_cards.generate", "ReportCard",
               new_value=f"class={class_id} period={academic_period_id} count={created_or_updated}")
    return {"status": "ok", "generated": created_or_updated}


@router.get("/classes/{class_id}/report-cards", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def list_class_report_cards(class_id: int, academic_period_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    """Liste les bulletins déjà générés pour une classe/période, avec le nom
    de l'élève — alimente l'écran académique de l'interface."""
    from app.models.students import Student

    cls = _class_access(db, current_user, class_id)
    period = _period_access(db, current_user, academic_period_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    report_cards = db.query(ReportCard).filter(
        ReportCard.class_id == class_id, ReportCard.academic_period_id == academic_period_id
    ).order_by(ReportCard.class_rank).all()

    result = []
    for rc in report_cards:
        student = db.get(Student, rc.student_id)
        result.append({
            "id": rc.id, "student_id": rc.student_id,
            "student_name": f"{student.first_name} {student.last_name}" if student else "—",
            "general_average": rc.general_average, "class_rank": rc.class_rank,
            "class_size": rc.class_size, "is_published": rc.is_published,
        })
    return result


@router.post("/report-cards/{report_card_id}/publish", dependencies=[Depends(require_permission("academic.report_cards.publish"))])
def publish_report_card(report_card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report_card = _report_card_access(db, current_user, report_card_id)
    report_card.is_published = True
    db.commit()
    return {"status": "ok"}


# ---------- Export PDF des bulletins (§23 du cahier des charges) ----------

def _report_card_pdf_context(db: Session, report_card: ReportCard) -> dict:
    from app.models.students import Student
    from app.models.organization import School, AcademicYear, AcademicPeriod

    student = db.get(Student, report_card.student_id)
    from app.models.students import SchoolClass
    school_class = db.get(SchoolClass, report_card.class_id)
    period = db.get(AcademicPeriod, report_card.academic_period_id)
    academic_year = db.get(AcademicYear, period.academic_year_id) if period else None
    school = db.get(School, student.school_id) if student else None

    _, subject_averages = compute_general_average(db, report_card.student_id, report_card.class_id, report_card.academic_period_id)

    return {
        "school_name": school.name if school else "SIGMA",
        "academic_year_label": academic_year.label if academic_year else "—",
        "period_name": period.name if period else "—",
        "student_full_name": f"{student.first_name} {student.last_name}" if student else "—",
        "student_matricule": student.matricule if student else "—",
        "class_name": school_class.name if school_class else "—",
        "subjects": [
            {"subject_name": s.subject_name, "average": s.average, "coefficient": s.coefficient}
            for s in subject_averages
        ],
        "general_average": report_card.general_average,
        "class_rank": report_card.class_rank,
        "class_size": report_card.class_size,
        "appreciation": report_card.appreciation,
    }


@router.get("/report-cards/{report_card_id}/pdf", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def download_report_card_pdf(report_card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report_card = _report_card_access(db, current_user, report_card_id)

    context = _report_card_pdf_context(db, report_card)
    content = generate_report_card_pdf(
        school_name=context["school_name"], academic_year_label=context["academic_year_label"],
        period_name=context["period_name"], student_full_name=context["student_full_name"],
        student_matricule=context["student_matricule"], class_name=context["class_name"],
        subjects=context["subjects"], general_average=context["general_average"],
        class_rank=context["class_rank"], class_size=context["class_size"], appreciation=context["appreciation"],
    )
    filename = f"bulletin_{context['student_matricule']}.pdf"
    return Response(content=content, media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/classes/{class_id}/report-cards/pdf", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def download_class_report_cards_pdf(class_id: int, academic_period_id: int, db: Session = Depends(get_db),
                                     current_user: User = Depends(get_current_user)):
    """Impression en lot: tous les bulletins d'une classe pour une période, en un seul PDF."""
    cls = _class_access(db, current_user, class_id)
    period = _period_access(db, current_user, academic_period_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(status_code=400, detail="Période incompatible avec la classe")
    report_cards = db.query(ReportCard).filter(
        ReportCard.class_id == class_id, ReportCard.academic_period_id == academic_period_id
    ).all()
    if not report_cards:
        raise HTTPException(status_code=404, detail="Aucun bulletin généré pour cette classe/période. Lancez d'abord /report-cards/generate.")

    contexts = [_report_card_pdf_context(db, rc) for rc in report_cards]
    content = generate_report_cards_batch_pdf(contexts)
    return Response(content=content, media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename=bulletins_classe_{class_id}.pdf"})
