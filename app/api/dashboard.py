import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, and_
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.students import Student, ClassMembership, SchoolClass
from app.models.security import User, UserPost, Post
from app.models.finance import Invoice, Payment
from app.models.academic import Grade, ReportCard, Assessment, TeacherAssignment
from app.models.attendance import AttendanceRecord
from app.services.cloud import enforce_subscription_feature, SubscriptionError

router = APIRouter(prefix="/api/dashboard", tags=["Pilotage"])


def _assert_school_access(school_id: int, current_user: User) -> None:
    if school_id != current_user.school_id and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès refusé")


@router.get("/summary")
def dashboard_summary(school_id: int, academic_year_id: int | None = None, academic_period_id: int | None = None,
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Indicateurs de direction (cahier des charges §36): élèves, personnel,
    classes, taux de réussite, moyenne générale, impayés, encaissements,
    absences.
    """
    _assert_school_access(school_id, current_user)

    students_count = db.query(func.count(Student.id)).filter(
        Student.school_id == school_id, Student.status == "active"
    ).scalar() or 0

    staff_count = db.query(func.count(User.id)).filter(
        User.school_id == school_id, User.is_active.is_(True)
    ).scalar() or 0

    classes_count_query = db.query(func.count(SchoolClass.id)).filter(
        SchoolClass.school_id == school_id, SchoolClass.is_active.is_(True)
    )
    if academic_year_id:
        classes_count_query = classes_count_query.filter(SchoolClass.academic_year_id == academic_year_id)
    classes_count = classes_count_query.scalar() or 0

    invoice_q = db.query(func.count(Invoice.id)).join(Student, Student.id == Invoice.student_id).filter(
        Student.school_id == school_id, Invoice.status.in_(["pending", "partially_paid", "overdue"])
    )
    due_q = db.query(func.coalesce(func.sum(Invoice.amount_due - Invoice.discount_amount), 0)).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == school_id)
    if academic_year_id:
        invoice_q = invoice_q.filter(Invoice.academic_year_id == academic_year_id)
        due_q = due_q.filter(Invoice.academic_year_id == academic_year_id)
    unpaid_invoices = invoice_q.scalar() or 0
    total_due = due_q.scalar() or 0
    total_collected = db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Student, Student.id == Payment.student_id).filter(
        Student.school_id == school_id, Payment.is_cancelled.is_(False)
    ).scalar() or 0

    result = {
        "effectif_eleves": students_count,
        "effectif_personnel": staff_count,
        "nombre_classes": classes_count,
        "factures_impayees": unpaid_invoices,
        "montant_du": float(total_due),
        "montant_encaisse": float(total_collected),
        "taux_recouvrement": round(float(total_collected) / float(total_due) * 100, 1) if total_due else None,
    }

    if academic_period_id:
        general_average = db.query(func.avg(ReportCard.general_average)).join(Student, Student.id == ReportCard.student_id).filter(
            Student.school_id == school_id, ReportCard.academic_period_id == academic_period_id, ReportCard.general_average.isnot(None)
        ).scalar()

        total_report_cards = db.query(func.count(ReportCard.id)).join(Student, Student.id == ReportCard.student_id).filter(
            Student.school_id == school_id, ReportCard.academic_period_id == academic_period_id
        ).scalar() or 0
        passing_report_cards = db.query(func.count(ReportCard.id)).join(Student, Student.id == ReportCard.student_id).filter(
            Student.school_id == school_id, ReportCard.academic_period_id == academic_period_id, ReportCard.general_average >= 10
        ).scalar() or 0

        absences_total = db.query(func.count(AttendanceRecord.id)).join(Student, Student.id == AttendanceRecord.student_id).filter(
            Student.school_id == school_id, AttendanceRecord.status == "absent"
        ).scalar() or 0
        records_total = db.query(func.count(AttendanceRecord.id)).join(Student, Student.id == AttendanceRecord.student_id).filter(
            Student.school_id == school_id
        ).scalar() or 0

        result.update({
            "moyenne_generale_ecole": round(float(general_average), 2) if general_average else None,
            "taux_reussite": round(passing_report_cards / total_report_cards * 100, 1) if total_report_cards else None,
            "taux_absenteisme": round(absences_total / records_total * 100, 1) if records_total else None,
        })

    return result


@router.get("/alerts")
def dashboard_alerts(school_id: int, academic_period_id: int | None = None, low_average_threshold: float = 8.0,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Alertes intelligentes (cahier des charges §37): élèves en difficulté,
    enseignants n'ayant pas terminé leurs notes, impayés en retard.
    """
    _assert_school_access(school_id, current_user)
    alerts = []

    if academic_period_id:
        weak_students = db.query(func.count(ReportCard.id)).join(Student, Student.id == ReportCard.student_id).filter(
            Student.school_id == school_id, ReportCard.academic_period_id == academic_period_id,
            ReportCard.general_average < low_average_threshold,
        ).scalar() or 0
        if weak_students:
            alerts.append({
                "level": "critical",
                "message": f"{weak_students} élève(s) ont une moyenne < {low_average_threshold}/20",
            })

        pending_assessments = (
            db.query(Assessment.id, Assessment.created_by_id)
            .join(Grade, Grade.assessment_id == Assessment.id)
            .join(Student, Student.id == Grade.student_id)
            .filter(Student.school_id == school_id, Assessment.academic_period_id == academic_period_id, Grade.state == "draft")
            .distinct()
            .all()
        )
        teachers_pending = {row.created_by_id for row in pending_assessments}
        if teachers_pending:
            alerts.append({
                "level": "warning",
                "message": f"{len(teachers_pending)} enseignant(s) n'ont pas encore soumis toutes leurs notes",
            })

    draft_grades = db.query(func.count(Grade.id)).join(Student, Student.id == Grade.student_id).filter(Student.school_id == school_id, Grade.state == "draft").scalar() or 0
    if draft_grades:
        alerts.append({"level": "info", "message": f"{draft_grades} note(s) au total encore en brouillon"})

    overdue_invoices = db.query(func.count(Invoice.id)).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == school_id, Invoice.status == "overdue").scalar() or 0
    if overdue_invoices:
        alerts.append({"level": "warning", "message": f"{overdue_invoices} dossier(s) financier(s) en retard"})

    return {"alerts": alerts}


@router.get("/action-items")
def dashboard_action_items(school_id: int, academic_year_id: int | None = None, academic_period_id: int | None = None, low_average_threshold: float = 8.0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Décisions opérationnelles priorisées, bornées à l'établissement courant."""
    _assert_school_access(school_id, current_user)
    items = []

    q = db.query(func.count(ReportCard.id)).join(Student, Student.id == ReportCard.student_id).filter(Student.school_id == school_id, ReportCard.general_average < low_average_threshold)
    if academic_period_id: q = q.filter(ReportCard.academic_period_id == academic_period_id)
    n = q.scalar() or 0
    if n: items.append({"key":"students_at_risk","level":"critical","count":n,"title":"Élèves à suivre","message":f"{n} élève(s) ont une moyenne inférieure à {low_average_threshold}/20.","action_label":"Ouvrir les dossiers","action_href":"/dashboard/students.html?filter=at-risk"})

    q = db.query(func.count(Invoice.id)).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == school_id, Invoice.status == "overdue")
    if academic_year_id: q = q.filter(Invoice.academic_year_id == academic_year_id)
    n = q.scalar() or 0
    if n: items.append({"key":"overdue_invoices","level":"warning","count":n,"title":"Impayés en retard","message":f"{n} dossier(s) financier(s) nécessitent une relance.","action_label":"Voir les impayés","action_href":"/dashboard/finance.html?filter=overdue"})

    q = db.query(func.count(Grade.id)).join(Student, Student.id == Grade.student_id).join(Assessment, Assessment.id == Grade.assessment_id).filter(Student.school_id == school_id, Grade.state == "draft")
    if academic_period_id: q = q.filter(Assessment.academic_period_id == academic_period_id)
    n = q.scalar() or 0
    if n: items.append({"key":"draft_grades","level":"info","count":n,"title":"Notes en brouillon","message":f"{n} note(s) sont encore en brouillon.","action_label":"Contrôler les évaluations","action_href":"/dashboard/evaluations.html?filter=draft"})

    q = db.query(func.count(ReportCard.id)).join(Student, Student.id == ReportCard.student_id).filter(Student.school_id == school_id, ReportCard.is_published.is_(False))
    if academic_period_id: q = q.filter(ReportCard.academic_period_id == academic_period_id)
    n = q.scalar() or 0
    if n: items.append({"key":"pending_report_cards","level":"warning","count":n,"title":"Bulletins non publiés","message":f"{n} bulletin(s) restent à contrôler et publier.","action_label":"Préparer les bulletins","action_href":"/dashboard/evaluations.html?filter=report-cards"})

    try:
        from app.models.documents import IdCard
        n = db.query(func.count(Student.id)).outerjoin(IdCard, and_(IdCard.student_id == Student.id, IdCard.is_active.is_(True))).filter(Student.school_id == school_id, Student.status == "active", IdCard.id.is_(None)).scalar() or 0
    except Exception as exc:
        logger.exception("Impossible de calculer les badges manquants: %s", exc)
        n = 0
    if n: items.append({"key":"missing_badges","level":"info","count":n,"title":"Badges manquants","message":f"{n} élève(s) actif(s) n'ont pas de badge actif.","action_label":"Générer les badges","action_href":"/dashboard/cards.html?filter=missing"})

    priority={"critical":0,"warning":1,"info":2}
    items.sort(key=lambda x:(priority[x["level"]],-x["count"]))
    return {"items":items,"total":sum(x["count"] for x in items)}


@router.get("/evolution")
def dashboard_evolution(class_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Évolution de la moyenne générale d'une classe, période par période (§38)."""
    rows = (db.query(ReportCard.academic_period_id, func.avg(ReportCard.general_average))
            .join(SchoolClass, SchoolClass.id == ReportCard.class_id)
            .filter(ReportCard.class_id == class_id, SchoolClass.school_id == current_user.school_id, ReportCard.general_average.isnot(None))
            .group_by(ReportCard.academic_period_id)
            .order_by(ReportCard.academic_period_id.asc())
            .all())
    return [{"academic_period_id": period_id, "moyenne_classe": round(float(avg), 2)} for period_id, avg in rows if avg is not None]


@router.get("/stats.pdf")
def dashboard_stats_pdf(school_id: int, academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.pdf_engine import generate_dashboard_stats_pdf
    from app.models.organization import School
    _assert_school_access(school_id, current_user)
    school = db.get(School, school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    if academic_year_id is not None:
        from app.models.organization import AcademicYear
        year = db.get(AcademicYear, academic_year_id)
        if year is None or year.school_id != school_id:
            raise HTTPException(status_code=400, detail="Année scolaire incompatible avec l'établissement")
    year_id = academic_year_id
    students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    classes_q = db.query(SchoolClass).filter(SchoolClass.school_id == school_id, SchoolClass.is_active.is_(True))
    if year_id: classes_q = classes_q.filter(SchoolClass.academic_year_id == year_id)
    classes = classes_q.all()
    class_ids = [c.id for c in classes]
    membership_counts = {}
    if class_ids:
        rows = (db.query(ClassMembership.class_id, func.count(ClassMembership.student_id))
                .filter(ClassMembership.class_id.in_(class_ids), ClassMembership.left_at.is_(None))
                .group_by(ClassMembership.class_id).all())
        membership_counts = {class_id: int(count or 0) for class_id, count in rows}
    levels = {}
    for c in classes:
        levels[c.level_id] = levels.get(c.level_id, 0) + membership_counts.get(c.id, 0)
    names = {l.id:l.name for l in db.query(__import__('app.models.students', fromlist=['Level']).Level).filter_by(school_id=school_id).all()}
    rows = [{"level_name":names.get(k,"—"),"effectif":v} for k,v in levels.items()]
    content=generate_dashboard_stats_pdf(school.name if school else "SIGMA", students, len(classes), rows)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition":"attachment; filename=statistiques_sigma.pdf"})

@router.get("/insight")
def dashboard_insight(school_id: int, academic_year_id: int | None = None,
                     academic_period_id: int | None = None,
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Cockpit SIGMA INSIGHT : synthèse pédagogique, présence et finance."""
    _assert_school_access(school_id, current_user)
    try:
        enforce_subscription_feature(db, school_id, "insight")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    from app.services.insight_engine import school_insight
    return school_insight(db, school_id, academic_year_id, academic_period_id)
