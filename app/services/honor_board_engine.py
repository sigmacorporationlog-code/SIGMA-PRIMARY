from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.academic import Assessment, Grade, Subject, TeacherAssignment
from app.models.attendance import AttendanceRecord
from app.models.organization import AcademicPeriod
from app.models.students import ClassMembership, SchoolClass, Student

SCORE_QUANT = Decimal("0.01")


def _q(value) -> Decimal:
    return Decimal(str(value)).quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


def resolve_scope(db: Session, school_id: int, academic_period_id: int, class_id: int | None, level_id: int | None, stream_id: int | None) -> tuple[AcademicPeriod, list[SchoolClass]]:
    period = db.get(AcademicPeriod, academic_period_id)
    if period is None:
        raise ValueError("Période scolaire introuvable")
    query = db.query(SchoolClass).filter(
        SchoolClass.school_id == school_id,
        SchoolClass.academic_year_id == period.academic_year_id,
    )
    if class_id is not None:
        query = query.filter(SchoolClass.id == class_id)
    if level_id is not None:
        query = query.filter(SchoolClass.level_id == level_id)
    if stream_id is not None:
        query = query.filter(SchoolClass.stream_id == stream_id)
    classes = query.order_by(SchoolClass.name.asc()).all()
    if not classes:
        raise ValueError("Aucune classe ne correspond au périmètre demandé")
    return period, classes


def calculate_entries(
    db: Session,
    school_id: int,
    academic_period_id: int,
    classes: list[SchoolClass],
    criteria: dict,
) -> list[dict]:
    class_ids = [c.id for c in classes]
    period = db.get(AcademicPeriod, academic_period_id)
    if period is None:
        raise ValueError("Période scolaire introuvable")
    membership_rows = (
        db.query(ClassMembership.student_id, ClassMembership.class_id)
        .join(Student, Student.id == ClassMembership.student_id)
        .filter(
            ClassMembership.class_id.in_(class_ids),
            ClassMembership.academic_year_id == classes[0].academic_year_id,
            ClassMembership.left_at.is_(None),
            Student.school_id == school_id,
        )
        .all()
    )
    student_classes: dict[int, int] = {student_id: class_id for student_id, class_id in membership_rows}
    if not student_classes:
        return []

    coeff_rows = (
        db.query(TeacherAssignment.class_id, TeacherAssignment.subject_id, TeacherAssignment.coefficient, Subject.default_coefficient, Subject.name)
        .join(Subject, Subject.id == TeacherAssignment.subject_id)
        .filter(TeacherAssignment.class_id.in_(class_ids))
        .all()
    )
    coefficients: dict[tuple[int, int], tuple[Decimal, str]] = {}
    for class_id, subject_id, assignment_coeff, default_coeff, name in coeff_rows:
        raw = assignment_coeff if assignment_coeff is not None else default_coeff
        if raw is not None and float(raw) > 0:
            coefficients.setdefault((class_id, subject_id), (_q(raw), name))

    assessment_rows = (
        db.query(
            Assessment.class_id,
            Assessment.subject_id,
            Assessment.max_score,
            Assessment.coefficient,
            Grade.student_id,
            Grade.score,
            Grade.is_absent,
        )
        .outerjoin(
            Grade,
            and_(
                Grade.assessment_id == Assessment.id,
                Grade.student_id.in_(student_classes.keys()),
                Grade.state.in_(("validated", "locked", "published")),
            ),
        )
        .filter(
            Assessment.academic_period_id == academic_period_id,
            Assessment.class_id.in_(class_ids),
            Assessment.is_active.is_(True),
        )
        .all()
    )

    subject_sums: dict[tuple[int, int, int], Decimal] = defaultdict(Decimal)
    subject_weights: dict[tuple[int, int, int], Decimal] = defaultdict(Decimal)
    for class_id, subject_id, max_score, eval_coeff, student_id, score, is_absent in assessment_rows:
        if student_id is None or student_classes.get(student_id) != class_id or score is None or is_absent:
            continue
        coeff_info = coefficients.get((class_id, subject_id))
        if not coeff_info or eval_coeff is None or float(eval_coeff) <= 0:
            continue
        normalized = (Decimal(str(score)) / Decimal(str(max_score))) * Decimal("20") if max_score and float(max_score) > 0 else Decimal(str(score))
        key = (student_id, class_id, subject_id)
        subject_sums[key] += normalized * Decimal(str(eval_coeff))
        subject_weights[key] += Decimal(str(eval_coeff))

    student_subject_avg: dict[tuple[int, int], list[Decimal]] = defaultdict(list)
    student_totals: dict[int, Decimal] = defaultdict(Decimal)
    student_coeffs: dict[int, Decimal] = defaultdict(Decimal)
    for (student_id, class_id, subject_id), total in subject_sums.items():
        weight = subject_weights[(student_id, class_id, subject_id)]
        if not weight:
            continue
        avg = _q(total / weight)
        subject_student_key = (student_id, class_id)
        student_subject_avg[subject_student_key].append(avg)
        subject_coeff = coefficients.get((class_id, subject_id), (Decimal("0"), ""))[0]
        student_totals[student_id] += avg * subject_coeff
        student_coeffs[student_id] += subject_coeff

    absent_rows = (
        db.query(AttendanceRecord.student_id, func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.student_id.in_(student_classes.keys()),
            AttendanceRecord.class_id.in_(class_ids),
            AttendanceRecord.date >= period.start_date,
            AttendanceRecord.date <= period.end_date,
            AttendanceRecord.status == "absent",
            AttendanceRecord.is_justified.is_(False),
        )
        .group_by(AttendanceRecord.student_id)
        .all()
    )
    unjustified = {student_id: int(count) for student_id, count in absent_rows}

    students = db.query(Student).filter(Student.id.in_(student_classes.keys())).all()
    class_map = {c.id: c for c in classes}
    min_average = Decimal(str(criteria["min_average"])) if criteria.get("min_average") is not None else None
    min_subject_average = Decimal(str(criteria["min_subject_average"])) if criteria.get("min_subject_average") is not None else None
    max_unjustified = int(criteria["max_unjustified_absences"]) if criteria.get("max_unjustified_absences") is not None else None
    require_all_subjects = bool(criteria.get("require_all_subjects_scored", False))
    excluded = set(criteria.get("exclude_statuses", ["excluded", "dropped_out"]))

    raw = []
    for student in students:
        class_id = student_classes.get(student.id)
        if class_id not in class_map or student.status in excluded or student_coeffs[student.id] <= 0:
            continue
        score = _q(student_totals[student.id] / student_coeffs[student.id])
        subject_values = student_subject_avg.get((student.id, class_id), [])
        if min_average is not None and score < min_average:
            continue
        if max_unjustified is not None and unjustified.get(student.id, 0) > max_unjustified:
            continue
        if min_subject_average is not None and (not subject_values or min(subject_values) < min_subject_average):
            continue
        if require_all_subjects:
            active_subject_ids = {subject_id for (cid, subject_id) in coefficients if cid == class_id}
            scored_subject_ids = {subject_id for (sid, cid, subject_id) in subject_sums if sid == student.id and cid == class_id}
            if not active_subject_ids.issubset(scored_subject_ids):
                continue
        raw.append({
            "student_id": student.id,
            "student_name": f"{student.last_name} {student.first_name}".strip(),
            "matricule": student.matricule,
            "class_id": class_id,
            "class_name": class_map[class_id].name,
            "score": float(score),
            "unjustified_absences": unjustified.get(student.id, 0),
        })

    raw.sort(key=lambda row: (-row["score"], row["last_name"] if "last_name" in row else row["student_name"], row["student_id"]))
    rank = 0
    previous_score = None
    for index, row in enumerate(raw, start=1):
        if previous_score != row["score"]:
            rank = index
            previous_score = row["score"]
        row["rank"] = rank
    return raw
