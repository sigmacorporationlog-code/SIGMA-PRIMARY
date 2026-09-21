"""Services de lecture sécurisée du portail parent SIGMA V4.17.

Le parent ne peut consulter que les élèves explicitement liés à son compte
Guardian.user_id. Les données exposées sont volontairement limitées au suivi
scolaire utile au foyer.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.students import Guardian, StudentGuardian, Student, ClassMembership, SchoolClass
from app.models.organization import AcademicYear, AcademicPeriod
from app.models.academic import ReportCard, Grade, Assessment, Subject
from app.models.attendance import AttendanceRecord
from app.models.finance import Invoice, Payment
from app.models.security import User


def get_guardian_for_user(db: Session, user: User) -> Guardian:
    guardian = db.query(Guardian).filter(Guardian.user_id == user.id, Guardian.school_id == user.school_id, Guardian.is_active.is_(True)).first()
    return guardian


def linked_students(db: Session, guardian: Guardian) -> list[Student]:
    rows = (
        db.query(Student)
        .join(StudentGuardian, StudentGuardian.student_id == Student.id)
        .filter(StudentGuardian.guardian_id == guardian.id, Student.school_id == guardian.school_id, Student.is_active.is_(True))
        .order_by(Student.last_name, Student.first_name)
        .all()
    )
    return rows


def student_access(db: Session, guardian: Guardian, student_id: int) -> Student | None:
    return (
        db.query(Student)
        .join(StudentGuardian, StudentGuardian.student_id == Student.id)
        .filter(Student.id == student_id, StudentGuardian.guardian_id == guardian.id,
                Student.school_id == guardian.school_id, Student.is_active.is_(True))
        .first()
    )


def current_year(db: Session, school_id: int) -> AcademicYear | None:
    return db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True), AcademicYear.is_archived.is_(False)).first()


def child_overview(db: Session, guardian: Guardian, student: Student, academic_year_id: int | None = None) -> dict:
    year = db.get(AcademicYear, academic_year_id) if academic_year_id else current_year(db, guardian.school_id)
    if year is None or year.school_id != guardian.school_id:
        year = None

    membership = None
    if year:
        membership = (
            db.query(ClassMembership)
            .filter(ClassMembership.student_id == student.id, ClassMembership.academic_year_id == year.id,
                    ClassMembership.left_at.is_(None))
            .order_by(desc(ClassMembership.id)).first()
        )
    school_class = db.get(SchoolClass, membership.class_id) if membership else None

    cards_q = db.query(ReportCard).filter(ReportCard.student_id == student.id, ReportCard.is_published.is_(True))
    if year:
        cards_q = cards_q.join(AcademicPeriod, AcademicPeriod.id == ReportCard.academic_period_id).filter(AcademicPeriod.academic_year_id == year.id)
    cards = cards_q.order_by(desc(ReportCard.id)).all()
    periods = {p.id: p for p in db.query(AcademicPeriod).filter(AcademicPeriod.id.in_([c.academic_period_id for c in cards])).all()} if cards else {}

    attendance_q = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id)
    if year:
        attendance_q = attendance_q.join(SchoolClass, SchoolClass.id == AttendanceRecord.class_id).filter(
            SchoolClass.academic_year_id == year.id, SchoolClass.school_id == guardian.school_id)
    attendance = attendance_q.all()

    invoices_q = db.query(Invoice).filter(Invoice.student_id == student.id)
    payments_q = db.query(Payment).filter(Payment.student_id == student.id, Payment.is_cancelled.is_(False))
    if year:
        invoices_q = invoices_q.filter(Invoice.academic_year_id == year.id)
        payments_q = payments_q.join(Invoice, Invoice.id == Payment.invoice_id).filter(Invoice.academic_year_id == year.id)
    invoices = invoices_q.all()
    payments = payments_q.all()
    total_due = sum(max(0.0, float(i.amount_due - i.discount_amount)) for i in invoices if i.status != 'exempted')
    total_paid = sum(float(p.amount) for p in payments)

    recent_grades = []
    if year and membership:
        rows = (
            db.query(Grade, Assessment, Subject)
            .join(Assessment, Assessment.id == Grade.assessment_id)
            .join(Subject, Subject.id == Assessment.subject_id)
            .join(SchoolClass, SchoolClass.id == Assessment.class_id)
            .join(AcademicPeriod, AcademicPeriod.id == Assessment.academic_period_id)
            .filter(Grade.student_id == student.id, Grade.state == 'published', Assessment.class_id == membership.class_id,
                    AcademicPeriod.academic_year_id == year.id,
                    Subject.school_id == guardian.school_id,
                    SchoolClass.school_id == guardian.school_id)
            .order_by(desc(Grade.id)).limit(20).all()
        )
        recent_grades = [{
            'subject': subject.name, 'assessment': assessment.name,
            'score': grade.score, 'max_score': grade.assessment.max_score,
            'comment': grade.comment, 'period_id': assessment.academic_period_id,
        } for grade, assessment, subject in rows]

    return {
        'student': {'id': student.id, 'matricule': student.matricule, 'first_name': student.first_name, 'last_name': student.last_name, 'status': student.status},
        'academic_year': {'id': year.id, 'label': year.label} if year else None,
        'class': {'id': school_class.id, 'name': school_class.name} if school_class else None,
        'report_cards': [{'id': c.id, 'period_id': c.academic_period_id, 'period_name': periods.get(c.academic_period_id).name if periods.get(c.academic_period_id) else '—',
                          'average': c.general_average, 'rank': c.class_rank, 'class_size': c.class_size, 'appreciation': c.appreciation, 'download_available': bool(c.file_path)} for c in cards],
        'recent_grades': recent_grades,
        'attendance': {
            'present': sum(1 for a in attendance if a.status == 'present'),
            'absent': sum(1 for a in attendance if a.status == 'absent'),
            'late': sum(1 for a in attendance if a.status == 'late'),
            'justified_absences': sum(1 for a in attendance if a.status == 'absent' and a.is_justified),
        },
        'finance': {'total_due': round(total_due, 2), 'total_paid': round(total_paid, 2), 'balance': round(max(0.0, total_due - total_paid), 2)},
    }


def child_mobile_summary(db: Session, guardian: Guardian, student: Student, academic_year_id: int | None = None) -> dict:
    """Payload compact et mobile-first; réutilise les contrôles de child_overview."""
    overview = child_overview(db, guardian, student, academic_year_id)
    return {
        'student': overview['student'],
        'academic_year': overview['academic_year'],
        'class': overview['class'],
        'attendance': overview['attendance'],
        'finance': overview['finance'],
        'latest_report_card': overview['report_cards'][0] if overview['report_cards'] else None,
        'recent_grades': overview['recent_grades'][:8],
    }

def child_invoices(db: Session, guardian: Guardian, student: Student, academic_year_id: int | None = None) -> list[dict]:
    year = db.get(AcademicYear, academic_year_id) if academic_year_id else current_year(db, guardian.school_id)
    if year is None or year.school_id != guardian.school_id:
        return []
    invoices = (db.query(Invoice).filter(Invoice.student_id == student.id, Invoice.academic_year_id == year.id).order_by(Invoice.due_date, Invoice.id).all())
    result=[]
    for invoice in invoices:
        paid = sum(float(p.amount) for p in db.query(Payment).filter(Payment.invoice_id == invoice.id, Payment.is_cancelled.is_(False)).all())
        due = max(0.0, float(invoice.amount_due - invoice.discount_amount))
        result.append({'id': invoice.id, 'status': invoice.status, 'amount_due': round(due,2), 'amount_paid': round(paid,2), 'balance': round(max(0.0,due-paid),2), 'due_date': invoice.due_date.isoformat() if invoice.due_date else None})
    return result
