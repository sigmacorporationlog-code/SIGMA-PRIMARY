from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
import app.models  # noqa: F401 - register every mapped table
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.students import Level, SchoolClass, Student, ClassMembership
from app.models.security import User
from app.models.academic import Subject, TeacherAssignment, Assessment, Grade, HonorBoardRule, HonorBoardEntry
from app.models.attendance import AttendanceRecord
from app.services.honor_board_engine import resolve_scope, calculate_entries


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_honor_board_filters_scores_and_assigns_tied_rank():
    db = _session()
    school = School(name="École SIGMA", ministry_name="Éducation")
    db.add(school); db.flush()
    year = AcademicYear(school_id=school.id, label="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_current=True)
    level = Level(school_id=school.id, name="CM2", order_index=1)
    db.add_all([year, level]); db.flush()
    cls = SchoolClass(school_id=school.id, academic_year_id=year.id, level_id=level.id, name="CM2 A")
    db.add(cls); db.flush()
    period = AcademicPeriod(academic_year_id=year.id, name="Trimestre 1", order_index=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 20), is_grade_entry_open=False, is_locked=True)
    db.add(period)
    creator = User(school_id=school.id, username="teacher", hashed_password="x", first_name="T", last_name="Prof")
    db.add(creator); db.flush()
    students = [
        Student(school_id=school.id, matricule="S001", first_name="A", last_name="Alpha"),
        Student(school_id=school.id, matricule="S002", first_name="B", last_name="Beta"),
        Student(school_id=school.id, matricule="S003", first_name="C", last_name="Gamma"),
    ]
    db.add_all(students); db.flush()
    db.add_all([ClassMembership(student_id=s.id, class_id=cls.id, academic_year_id=year.id, enrolled_at=date(2026,9,1)) for s in students])
    subject = Subject(school_id=school.id, name="Mathématiques", default_coefficient=2)
    db.add(subject); db.flush()
    db.add(TeacherAssignment(academic_year_id=year.id, teacher_id=creator.id, subject_id=subject.id, class_id=cls.id, coefficient=2, weekly_hours=4))
    assessment = Assessment(academic_period_id=period.id, subject_id=subject.id, class_id=cls.id, created_by_id=creator.id, name="Composition", assessment_type="composition", max_score=20, coefficient=1)
    db.add(assessment); db.flush()
    db.add_all([
        Grade(assessment_id=assessment.id, student_id=students[0].id, score=16, state="validated"),
        Grade(assessment_id=assessment.id, student_id=students[1].id, score=16, state="validated"),
        Grade(assessment_id=assessment.id, student_id=students[2].id, score=10, state="validated"),
    ])
    db.add(AttendanceRecord(student_id=students[2].id, class_id=cls.id, date=date(2026, 10, 1), status="absent", is_justified=False, recorded_by_id=creator.id))
    db.commit()

    rule = {"min_average": 14, "max_unjustified_absences": 0, "exclude_statuses": ["excluded", "dropped_out"]}
    period, classes = resolve_scope(db, school.id, period.id, cls.id, None, None)
    entries = calculate_entries(db, school.id, period.id, classes, rule)

    assert [e["student_id"] for e in entries] == [students[0].id, students[1].id]
    assert [e["rank"] for e in entries] == [1, 1]
    assert all(e["score"] == 16.0 for e in entries)


def test_honor_board_entry_history_is_unique():
    db = _session()
    school = School(name="School", ministry_name="Education")
    db.add(school); db.flush()
    year = AcademicYear(school_id=school.id, label="2026/2027", start_date=date(2026,9,1), end_date=date(2027,6,30))
    period = AcademicPeriod(academic_year_id=1, name="T1", order_index=1, start_date=date(2026,9,1), end_date=date(2026,12,20))
    level = Level(school_id=school.id, name="CM1", order_index=1)
    db.add_all([year, level]); db.flush()
    period.academic_year_id = year.id
    db.add(period); db.flush()
    rule = HonorBoardRule(school_id=school.id, name="Excellence", criteria={"min_average": 14})
    student = Student(school_id=school.id, matricule="X1", first_name="A", last_name="B")
    db.add_all([rule, student]); db.flush()
    db.add(HonorBoardEntry(rule_id=rule.id, student_id=student.id, academic_period_id=period.id, score=14, rank=1, is_validated=False))
    db.commit()
    db.add(HonorBoardEntry(rule_id=rule.id, student_id=student.id, academic_period_id=period.id, score=15, rank=1, is_validated=False))
    try:
        db.commit()
        assert False, "la contrainte d'unicité doit empêcher le doublon"
    except IntegrityError:
        db.rollback()
