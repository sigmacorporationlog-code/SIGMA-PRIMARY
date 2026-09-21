"""Vue de travail enseignant V4.17, limitée aux affectations de l'enseignant."""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.security import User
from app.models.academic import TeacherAssignment, Assessment, Grade, Subject
from app.models.organization import AcademicYear, AcademicPeriod
from app.models.students import SchoolClass, ClassMembership


def teacher_overview(db: Session, user: User, academic_year_id: int | None = None) -> dict:
    year = db.get(AcademicYear, academic_year_id) if academic_year_id else db.query(AcademicYear).filter(AcademicYear.school_id == user.school_id, AcademicYear.is_current.is_(True)).first()
    if year is None or year.school_id != user.school_id:
        return {'academic_year': None, 'classes': [], 'pending_assessments': [], 'kpis': {'classes': 0, 'students': 0, 'pending_grades': 0}}
    assignments = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == user.id, TeacherAssignment.academic_year_id == year.id).all()
    class_ids = sorted({a.class_id for a in assignments})
    classes = db.query(SchoolClass).filter(SchoolClass.id.in_(class_ids), SchoolClass.school_id == user.school_id).all() if class_ids else []
    class_map = {c.id: c for c in classes}
    subjects = {s.id: s for s in db.query(Subject).filter(Subject.school_id == user.school_id).all()}
    rows = []
    for a in assignments:
        c = class_map.get(a.class_id)
        if c:
            count = db.query(func.count(ClassMembership.id)).filter(ClassMembership.class_id == c.id, ClassMembership.left_at.is_(None)).scalar() or 0
            rows.append({'class_id': c.id, 'class_name': c.name, 'subject_id': a.subject_id, 'subject_name': subjects.get(a.subject_id).name if subjects.get(a.subject_id) else '—', 'student_count': count})
    assessments = db.query(Assessment).filter(Assessment.created_by_id == user.id).all()
    pending = []
    for a in assessments:
        if a.class_id not in class_map: continue
        total = db.query(func.count(ClassMembership.id)).filter(ClassMembership.class_id == a.class_id, ClassMembership.left_at.is_(None)).scalar() or 0
        entered = db.query(func.count(Grade.id)).filter(Grade.assessment_id == a.id).scalar() or 0
        if entered < total:
            pending.append({'assessment_id': a.id, 'name': a.name, 'class_id': a.class_id, 'class_name': class_map[a.class_id].name, 'entered': entered, 'total': total, 'remaining': max(0, total-entered)})
    return {'academic_year': {'id': year.id, 'label': year.label}, 'classes': rows, 'pending_assessments': pending,
            'kpis': {'classes': len(class_ids), 'students': sum(r['student_count'] for r in rows if r['class_id'] in class_ids), 'pending_grades': sum(x['remaining'] for x in pending)}}


def teacher_class_roster(db: Session, user: User, class_id: int, academic_year_id: int | None = None) -> dict:
    year = db.get(AcademicYear, academic_year_id) if academic_year_id else db.query(AcademicYear).filter(AcademicYear.school_id == user.school_id, AcademicYear.is_current.is_(True)).first()
    if year is None or year.school_id != user.school_id:
        return {'academic_year': None, 'class': None, 'students': []}
    allowed = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == user.id, TeacherAssignment.academic_year_id == year.id, TeacherAssignment.class_id == class_id).first()
    klass = db.query(SchoolClass).filter(SchoolClass.id == class_id, SchoolClass.school_id == user.school_id, SchoolClass.academic_year_id == year.id).first()
    if not allowed or not klass:
        return {'academic_year': {'id': year.id, 'label': year.label}, 'class': None, 'students': []}
    memberships = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.academic_year_id == year.id, ClassMembership.left_at.is_(None)).all()
    student_ids = [m.student_id for m in memberships]
    from app.models.students import Student
    students = db.query(Student).filter(Student.id.in_(student_ids), Student.school_id == user.school_id, Student.is_active.is_(True)).order_by(Student.last_name, Student.first_name).all() if student_ids else []
    return {'academic_year': {'id': year.id, 'label': year.label}, 'class': {'id': klass.id, 'name': klass.name}, 'students': [{'id': s.id, 'matricule': s.matricule, 'first_name': s.first_name, 'last_name': s.last_name} for s in students]}
