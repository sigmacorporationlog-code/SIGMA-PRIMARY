from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

import app.models  # noqa: F401
from app.core.database import Base
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.security import User
from app.models.students import Guardian, Student, StudentGuardian, SchoolClass, ClassMembership
from app.models.academic import TeacherAssignment, Subject, Assessment, Grade, ReportCard
from app.services.parent_portal import get_guardian_for_user, linked_students, student_access, child_overview
from app.services.teacher_portal import teacher_overview


def setup_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    school = School(name='Portal School', currency='XAF', language='fr')
    db.add(school); db.flush()
    year = AcademicYear(school_id=school.id, label='2026/2027', start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_current=True)
    period = AcademicPeriod(academic_year_id=year.id, name='Trimestre 1', order_index=1, start_date=date(2026,9,1), end_date=date(2026,12,20))
    db.add(year); db.flush(); period.academic_year_id = year.id; db.add(period); db.flush()
    parent_user = User(school_id=school.id, username='parent', hashed_password='x', first_name='Parent', last_name='One')
    teacher = User(school_id=school.id, username='teacher', hashed_password='x', first_name='Teacher', last_name='One')
    db.add_all([parent_user, teacher]); db.flush()
    guardian = Guardian(school_id=school.id, first_name='Parent', last_name='One', relationship_type='mère', user_id=parent_user.id)
    student = Student(school_id=school.id, matricule='S-001', first_name='Ali', last_name='Test')
    other = Student(school_id=school.id, matricule='S-002', first_name='Other', last_name='Test')
    db.add_all([guardian, student, other]); db.flush()
    db.add(StudentGuardian(student_id=student.id, guardian_id=guardian.id, is_primary_contact=True))
    from app.models.academic import Subject
    subject = Subject(school_id=school.id, name='Maths')
    db.add(subject); db.flush()
    klass = SchoolClass(school_id=school.id, academic_year_id=year.id, level_id=1, name='6e A')
    # level FK must exist for SQLite integrity only when enforced; create level first
    from app.models.students import Level
    lev = Level(school_id=school.id, name='6e', order_index=1); db.add(lev); db.flush(); klass.level_id = lev.id
    db.add(klass); db.flush()
    db.add(ClassMembership(student_id=student.id, class_id=klass.id, academic_year_id=year.id, enrolled_at=date(2026,9,1)))
    db.add(TeacherAssignment(academic_year_id=year.id, teacher_id=teacher.id, subject_id=subject.id, class_id=klass.id))
    db.commit()
    return db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject


def test_parent_sees_only_linked_children():
    db, *_ = setup_db()
    guardian = get_guardian_for_user(db, db.query(User).filter_by(username='parent').one())
    assert [s.matricule for s in linked_students(db, guardian)] == ['S-001']
    assert student_access(db, guardian, 2) is None


def test_parent_overview_is_scoped_and_safe():
    db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject = setup_db()
    overview = child_overview(db, guardian, student)
    assert overview['academic_year']['label'] == '2026/2027'
    assert overview['class']['name'] == '6e A'
    assert overview['finance']['balance'] >= 0


def test_teacher_overview_only_contains_own_assignments():
    db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject = setup_db()
    overview = teacher_overview(db, teacher)
    assert overview['kpis']['classes'] == 1
    assert overview['classes'][0]['subject_name'] == 'Maths'
