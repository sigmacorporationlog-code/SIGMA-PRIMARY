"""Moteur académique déterministe et Decimal.

Règle : données brutes -> normalisation sur 20 -> moyenne pondérée -> arrondi
explicite HALF_UP à deux décimales -> affichage/API.
"""
from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.academic import Assessment, Grade, Subject, TeacherAssignment
from app.models.students import ClassMembership

SCORE_QUANT = Decimal("0.01")


def to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def round_score(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


@dataclass
class SubjectAverage:
    subject_id: int
    subject_name: str
    average: Decimal | None
    coefficient: Decimal


def _assessment_rows(db: Session, student_ids: list[int], class_id: int, period_id: int):
    if not student_ids:
        return []
    return (
        db.query(
            Assessment.id,
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
                Grade.student_id.in_(student_ids),
                Grade.state.in_(("validated", "locked", "published")),
            ),
        )
        .filter(
            Assessment.academic_period_id == period_id,
            Assessment.class_id == class_id,
            Assessment.is_active.is_(True),
        )
        .all()
    )


def _subject_coefficients(db: Session, class_id: int) -> dict[int, tuple[Decimal, str]]:
    rows = (
        db.query(TeacherAssignment.subject_id, TeacherAssignment.coefficient, Subject.name, Subject.default_coefficient)
        .join(Subject, Subject.id == TeacherAssignment.subject_id)
        .filter(TeacherAssignment.class_id == class_id)
        .all()
    )
    result = {}
    for subject_id, assignment_coeff, name, default_coeff in rows:
        coeff = assignment_coeff if assignment_coeff is not None else default_coeff
        coeff_d = to_decimal(coeff)
        if coeff_d <= 0:
            continue
        result.setdefault(subject_id, (coeff_d, name))
    return result


def _bulk_averages(db: Session, student_ids: list[int], class_id: int, period_id: int):
    coeffs = _subject_coefficients(db, class_id)
    sums: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    weights: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for row in _assessment_rows(db, student_ids, class_id, period_id):
        _, subject_id, max_score, eval_coeff, student_id, score, absent = row
        if student_id is None or subject_id not in coeffs or score is None or absent:
            continue
        eval_weight = to_decimal(eval_coeff)
        if eval_weight <= 0:
            continue
        max_score_d = to_decimal(max_score)
        score_d = to_decimal(score)
        normalized = (score_d / max_score_d) * Decimal("20") if max_score_d > 0 else score_d
        key = (student_id, subject_id)
        sums[key] += normalized * eval_weight
        weights[key] += eval_weight
    averages = {}
    for key, total in sums.items():
        weight = weights[key]
        if weight:
            averages[key] = round_score(total / weight)
    return averages, coeffs


def compute_subject_average(db: Session, student_id: int, subject_id: int, class_id: int, period_id: int) -> Decimal | None:
    averages, _ = _bulk_averages(db, [student_id], class_id, period_id)
    return averages.get((student_id, subject_id))


def compute_general_average(db: Session, student_id: int, class_id: int, period_id: int) -> tuple[Decimal | None, list[SubjectAverage]]:
    averages, coeffs = _bulk_averages(db, [student_id], class_id, period_id)
    subject_averages = []
    weighted_sum = Decimal("0")
    total_coeff = Decimal("0")
    for subject_id, (coeff, name) in coeffs.items():
        avg = averages.get((student_id, subject_id))
        subject_averages.append(SubjectAverage(subject_id, name, avg, coeff))
        if avg is not None:
            weighted_sum += avg * coeff
            total_coeff += coeff
    return (round_score(weighted_sum / total_coeff) if total_coeff else None), subject_averages


def compute_class_ranking(db: Session, class_id: int, period_id: int) -> list[tuple[int, Decimal]]:
    memberships = db.query(ClassMembership.student_id).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.left_at.is_(None),
    ).all()
    student_ids = [row[0] for row in memberships]
    averages, coeffs = _bulk_averages(db, student_ids, class_id, period_id)
    totals: dict[int, Decimal] = defaultdict(Decimal)
    weights: dict[int, Decimal] = defaultdict(Decimal)
    for (student_id, subject_id), avg in averages.items():
        coeff = coeffs[subject_id][0]
        totals[student_id] += avg * coeff
        weights[student_id] += coeff
    results = [
        (student_id, round_score(totals[student_id] / weights[student_id]))
        for student_id in student_ids if weights[student_id] > 0
    ]
    return sorted(results, key=lambda pair: (-pair[1], pair[0]))
