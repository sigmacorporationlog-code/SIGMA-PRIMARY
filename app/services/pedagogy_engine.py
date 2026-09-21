"""Moteur de pilotage pédagogique SIGMA V3.

Ce module fournit des indicateurs de décision, pas un diagnostic médical ou
psychologique. Le score de risque sert uniquement à prioriser les actions
pédagogiques de l'établissement.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationActivity, EvaluationResult
from app.models.students import ClassMembership, Student
from app.models.attendance import AttendanceRecord, DisciplinaryRecord


@dataclass
class StudentRisk:
    student_id: int
    score: int
    level: str
    reasons: list[str]


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def student_risk(db: Session, student_id: int, class_id: int, academic_period_id: int) -> StudentRisk:
    results = (
        db.query(EvaluationResult, EvaluationActivity)
        .join(EvaluationActivity, EvaluationResult.activity_id == EvaluationActivity.id)
        .filter(
            EvaluationResult.student_id == student_id,
            EvaluationActivity.class_id == class_id,
            EvaluationActivity.academic_period_id == academic_period_id,
        ).all()
    )
    scored = [r for r, a in results if not r.is_absent and r.score is not None and (r.max_score or a.max_score)]
    average = None
    if scored:
        values = []
        for r, a in results:
            maximum = r.max_score or a.max_score
            if not r.is_absent and r.score is not None and maximum:
                values.append((r.score / maximum) * 20)
        average = sum(values) / len(values) if values else None

    attendance = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.class_id == class_id,
    ).all()
    absences = sum(1 for x in attendance if x.status == "absent" and not x.is_justified)
    lates = sum(1 for x in attendance if x.status == "late")
    discipline = db.query(DisciplinaryRecord).filter(DisciplinaryRecord.student_id == student_id).all()
    severe = sum(1 for x in discipline if x.severity == "high" or x.record_type in ("sanction", "exclusion"))

    score = 0
    reasons: list[str] = []
    if average is not None and average < 10:
        score += 45
        reasons.append(f"moyenne faible ({average:.1f}/20)")
    elif average is not None and average < 12:
        score += 25
        reasons.append(f"moyenne à surveiller ({average:.1f}/20)")
    elif average is None:
        score += 10
        reasons.append("données d'évaluation insuffisantes")

    if absences >= 5:
        score += 25
        reasons.append(f"{absences} absences non justifiées")
    elif absences >= 2:
        score += 12
        reasons.append(f"{absences} absences non justifiées")
    if lates >= 5:
        score += 10
        reasons.append(f"{lates} retards")
    elif lates >= 2:
        score += 5
        reasons.append(f"{lates} retards")
    if severe:
        score += min(20, severe * 10)
        reasons.append(f"{severe} incident(s) disciplinaire(s) important(s)")

    score = _clamp(score)
    level = "critical" if score >= 60 else "warning" if score >= 30 else "normal"
    return StudentRisk(student_id, score, level, reasons)


def class_risk_snapshot(db: Session, class_id: int, academic_year_id: int, academic_period_id: int) -> list[dict]:
    memberships = db.query(ClassMembership).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.academic_year_id == academic_year_id,
        ClassMembership.left_at.is_(None),
    ).all()
    out = []
    for membership in memberships:
        student = db.get(Student, membership.student_id)
        if not student:
            continue
        risk = student_risk(db, student.id, class_id, academic_period_id)
        out.append({
            "student_id": student.id,
            "student_name": f"{student.first_name} {student.last_name}",
            "matricule": student.matricule,
            "score": risk.score,
            "level": risk.level,
            "reasons": risk.reasons,
        })
    return sorted(out, key=lambda x: (-x["score"], x["student_name"]))
