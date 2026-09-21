from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core.database import Base
import app.models  # noqa: F401
from app.models.organization import AcademicPeriod, AcademicYear, School
from app.models.students import ClassMembership, Level, SchoolClass, Student
from app.models.security import User
from app.models.academic import Assessment, Grade, Subject, TeacherAssignment
from app.services.grading_engine import compute_class_ranking


def build_dataset(engine, student_count: int) -> tuple[int, int]:
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        school = School(name="SIGMA Benchmark", ministry_name="Education")
        db.add(school)
        db.flush()
        year = AcademicYear(
            school_id=school.id,
            label="2026/2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )
        level = Level(school_id=school.id, name="CM2", order_index=1)
        db.add_all([year, level])
        db.flush()
        cls = SchoolClass(
            school_id=school.id,
            academic_year_id=year.id,
            level_id=level.id,
            name="CM2 BENCH",
        )
        period = AcademicPeriod(
            academic_year_id=year.id,
            name="T1",
            order_index=1,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 20),
            is_grade_entry_open=False,
            is_locked=True,
        )
        teacher = User(
            school_id=school.id,
            username="benchmark.teacher",
            hashed_password="x",
            first_name="Bench",
            last_name="Mark",
        )
        subject = Subject(school_id=school.id, name="Math", default_coefficient=2)
        db.add_all([cls, period, teacher, subject])
        db.flush()
        db.add(TeacherAssignment(
            academic_year_id=year.id,
            teacher_id=teacher.id,
            subject_id=subject.id,
            class_id=cls.id,
            coefficient=2,
            weekly_hours=4,
        ))
        db.flush()
        assessment = Assessment(
            academic_period_id=period.id,
            subject_id=subject.id,
            class_id=cls.id,
            created_by_id=teacher.id,
            name="Benchmark",
            assessment_type="composition",
            max_score=20,
            coefficient=1,
        )
        db.add(assessment)
        db.flush()

        students = [
            Student(
                school_id=school.id,
                matricule=f"B{idx:06d}",
                first_name=f"First{idx}",
                last_name="Bench",
            )
            for idx in range(student_count)
        ]
        db.add_all(students)
        db.flush()
        db.add_all([
            ClassMembership(
                student_id=s.id,
                class_id=cls.id,
                academic_year_id=year.id,
                enrolled_at=date(2026, 9, 1),
            )
            for s in students
        ])
        db.add_all([
            Grade(
                assessment_id=assessment.id,
                student_id=s.id,
                score=10 + (idx % 11) / 2,
                state="validated",
            )
            for idx, s in enumerate(students)
        ])
        db.commit()
        return cls.id, period.id


def run_case(student_count: int) -> dict:
    engine = create_engine("sqlite:///:memory:", future=True)
    class_id, period_id = build_dataset(engine, student_count)
    counter = {"statements": 0}

    def before_cursor_execute(*_args):
        counter["statements"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    start = time.perf_counter()
    with Session(engine) as db:
        results = compute_class_ranking(db, class_id, period_id)
    elapsed_ms = (time.perf_counter() - start) * 1000
    event.remove(engine, "before_cursor_execute", before_cursor_execute)
    return {
        "students": student_count,
        "ranking_rows": len(results),
        "sql_statements": counter["statements"],
        "elapsed_ms": round(elapsed_ms, 2),
        "queries_per_student": round(counter["statements"] / student_count, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--students", nargs="*", type=int, default=[100, 500, 1000, 5000])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = [run_case(max(1, n)) for n in args.students]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if args.output:
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
