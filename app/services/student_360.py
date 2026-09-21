from sqlalchemy.orm import Session

from app.models.academic import Grade, Assessment, ReportCard
from app.models.organization import AcademicPeriod, AcademicYear
from app.models.attendance import AttendanceRecord, DisciplinaryRecord
from app.models.documents import IdCard
from app.models.finance import Invoice, Payment
from app.models.students import ClassMembership, Guardian, Student, StudentGuardian


def build_student_360(db: Session, student: Student, academic_year_id: int | None = None) -> dict:
    """Vue transverse du dossier élève. Les agrégats restent séparés des modèles."""
    memberships_q = db.query(ClassMembership).filter(ClassMembership.student_id == student.id)
    if academic_year_id:
        memberships_q = memberships_q.filter(ClassMembership.academic_year_id == academic_year_id)
    memberships = memberships_q.order_by(ClassMembership.enrolled_at.desc()).all()
    current = next((m for m in memberships if m.left_at is None), None)

    guardians = []
    for link in db.query(StudentGuardian).filter(StudentGuardian.student_id == student.id).all():
        g = db.get(Guardian, link.guardian_id)
        if not g or not g.is_active:
            continue
        guardians.append({
            "id": g.id, "name": f"{g.first_name} {g.last_name}".strip(),
            "relationship": g.relationship_type, "phone": g.phone, "email": g.email,
            "is_primary": link.is_primary_contact,
        })

    grades_q = (db.query(Grade)
        .join(Assessment, Grade.assessment_id == Assessment.id)
        .join(AcademicPeriod, Assessment.academic_period_id == AcademicPeriod.id)
        .join(AcademicYear, AcademicPeriod.academic_year_id == AcademicYear.id)
        .filter(Grade.student_id == student.id))
    if academic_year_id:
        grades_q = grades_q.filter(AcademicPeriod.academic_year_id == academic_year_id)
    grades = grades_q.order_by(Grade.created_at.desc()).limit(30).all()

    attendance_q = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id)
    attendance = attendance_q.order_by(AttendanceRecord.created_at.desc()).limit(30).all()
    discipline = db.query(DisciplinaryRecord).filter(DisciplinaryRecord.student_id == student.id).order_by(DisciplinaryRecord.created_at.desc()).limit(20).all()

    invoices = db.query(Invoice).filter(Invoice.student_id == student.id).order_by(Invoice.created_at.desc()).limit(30).all()
    payments = db.query(Payment).filter(Payment.student_id == student.id).order_by(Payment.created_at.desc()).limit(30).all()
    cards = db.query(IdCard).filter(IdCard.student_id == student.id).order_by(IdCard.created_at.desc()).limit(10).all()
    reports = db.query(ReportCard).filter(ReportCard.student_id == student.id).order_by(ReportCard.created_at.desc()).limit(10).all()

    return {
        "student": {
            "id": student.id, "matricule": student.matricule,
            "first_name": student.first_name, "last_name": student.last_name,
            "birth_date": student.birth_date.isoformat() if student.birth_date else None,
            "sex": student.sex, "photo_path": student.photo_path, "status": student.status,
        },
        "current_enrollment": {
            "membership_id": current.id,
            "class_id": current.class_id,
            "class_name": current.school_class.name if current.school_class else None,
            "academic_year_id": current.academic_year_id,
            "enrolled_at": current.enrolled_at.isoformat(),
        } if current else None,
        "guardians": guardians,
        "school_history": [
            {"id": m.id, "class_id": m.class_id,
             "class_name": m.school_class.name if m.school_class else None,
             "academic_year_id": m.academic_year_id,
             "enrolled_at": m.enrolled_at.isoformat(),
             "left_at": m.left_at.isoformat() if m.left_at else None}
            for m in memberships
        ],
        "pedagogy": {
            "recent_grades": [
                {"id": g.id, "assessment_id": g.assessment_id, "score": g.score,
                 "comment": g.comment, "state": g.state} for g in grades
            ],
            "report_cards": [{"id": r.id, "published": r.is_published, "general_average": r.general_average, "class_rank": r.class_rank} for r in reports],
        },
        "attendance": [
            {"id": a.id, "date": getattr(a, "date", None).isoformat() if getattr(a, "date", None) else None,
             "status": getattr(a, "status", None), "justified": a.is_justified, "reason": a.justification_reason}
            for a in attendance
        ],
        "discipline": [
            {"id": d.id, "date": getattr(d, "date", None).isoformat() if getattr(d, "date", None) else None,
             "type": d.record_type, "severity": d.severity, "description": d.description}
            for d in discipline
        ],
        "finance": {
            "invoices": [{"id": i.id, "status": i.status, "amount_due": i.amount_due,
                          "discount_amount": i.discount_amount, "due_date": i.due_date.isoformat() if i.due_date else None} for i in invoices],
            "payments": [{"id": p.id, "amount": p.amount, "method": p.method, "paid_at": p.paid_at.isoformat(), "is_cancelled": p.is_cancelled} for p in payments],
        },
        "cards": [{"id": c.id, "status": "active" if c.is_active else "revoked", "card_number": c.card_number} for c in cards],
    }
