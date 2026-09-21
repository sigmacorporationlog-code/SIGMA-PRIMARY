"""SIGMA INSIGHT — pilotage décisionnel.

Les scores produits ici sont des indicateurs opérationnels et non des
 diagnostics médicaux, psychologiques ou sociaux.
"""
from __future__ import annotations

from collections import Counter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.students import Student, ClassMembership, SchoolClass
from app.models.academic import ReportCard, Assessment, Grade
from app.models.attendance import AttendanceRecord
from app.models.finance import Invoice, Payment
from app.services.pedagogy_engine import student_risk


def school_insight(db: Session, school_id: int, academic_year_id: int | None = None,
                   academic_period_id: int | None = None) -> dict:
    """Construit un cockpit décisionnel borné à un établissement."""
    students_q = db.query(Student).filter(Student.school_id == school_id, Student.status == "active")
    students = students_q.all()

    classes_q = db.query(SchoolClass).filter(SchoolClass.school_id == school_id, SchoolClass.is_active.is_(True))
    if academic_year_id:
        classes_q = classes_q.filter(SchoolClass.academic_year_id == academic_year_id)
    classes = classes_q.all()
    class_ids = {c.id for c in classes}

    risks: list[dict] = []
    if academic_period_id and class_ids:
        memberships = db.query(ClassMembership).filter(
            ClassMembership.class_id.in_(class_ids),
            ClassMembership.left_at.is_(None),
            *( [ClassMembership.academic_year_id == academic_year_id] if academic_year_id else [] ),
        ).all()
        seen: set[int] = set()
        for m in memberships:
            if m.student_id in seen:
                continue
            seen.add(m.student_id)
            student = next((s for s in students if s.id == m.student_id), None)
            if not student:
                continue
            risk = student_risk(db, student.id, m.class_id, academic_period_id)
            risks.append({"student_id": student.id, "student_name": f"{student.first_name} {student.last_name}",
                          "class_id": m.class_id, "score": risk.score, "level": risk.level, "reasons": risk.reasons})

    risk_counts = Counter(r["level"] for r in risks)
    top_risks = sorted(risks, key=lambda x: (-x["score"], x["student_name"]))[:10]

    overdue_q = db.query(func.count(Invoice.id)).join(Student, Student.id == Invoice.student_id).filter(
        Student.school_id == school_id, Invoice.status == "overdue")
    if academic_year_id:
        overdue_q = overdue_q.filter(Invoice.academic_year_id == academic_year_id)
    overdue = overdue_q.scalar() or 0

    due_q = db.query(func.coalesce(func.sum(Invoice.amount_due - Invoice.discount_amount), 0)).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == school_id)
    if academic_year_id:
        due_q = due_q.filter(Invoice.academic_year_id == academic_year_id)
    total_due = float(due_q.scalar() or 0)

    payment_q = db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Student, Student.id == Payment.student_id).filter(Student.school_id == school_id, Payment.is_cancelled.is_(False))
    total_collected = float(payment_q.scalar() or 0)

    attendance_q = db.query(AttendanceRecord).join(Student, Student.id == AttendanceRecord.student_id).filter(Student.school_id == school_id)
    attendance = attendance_q.all()
    absences = sum(1 for a in attendance if a.status == "absent")
    unjustified = sum(1 for a in attendance if a.status == "absent" and not a.is_justified)
    lates = sum(1 for a in attendance if a.status == "late")

    draft_q = db.query(func.count(Grade.id)).join(Student, Student.id == Grade.student_id).join(Assessment, Assessment.id == Grade.assessment_id).filter(Student.school_id == school_id, Grade.state == "draft")
    if academic_period_id:
        draft_q = draft_q.filter(Assessment.academic_period_id == academic_period_id)
    draft_grades = draft_q.scalar() or 0

    report_q = db.query(ReportCard).join(Student, Student.id == ReportCard.student_id).filter(Student.school_id == school_id)
    if academic_period_id:
        report_q = report_q.filter(ReportCard.academic_period_id == academic_period_id)
    reports = report_q.all()
    averages = [r.general_average for r in reports if r.general_average is not None]
    school_average = round(sum(averages) / len(averages), 2) if averages else None
    passing = sum(1 for x in averages if x >= 10)

    actions: list[dict] = []
    if risk_counts["critical"]:
        actions.append({"key":"critical_students","priority":"critical","count":risk_counts["critical"],"title":"Élèves prioritaires","action":"Ouvrir les dossiers Élève 360","href":"/dashboard/students.html?filter=at-risk"})
    if overdue:
        actions.append({"key":"overdue","priority":"warning","count":overdue,"title":"Impayés en retard","action":"Lancer une relance financière","href":"/dashboard/finance.html?filter=overdue"})
    if unjustified >= 5:
        actions.append({"key":"attendance","priority":"warning","count":unjustified,"title":"Absences non justifiées","action":"Contrôler les absences et contacter les responsables","href":"/dashboard/students.html?filter=attendance"})
    if draft_grades:
        actions.append({"key":"draft_grades","priority":"info","count":draft_grades,"title":"Notes à finaliser","action":"Ouvrir les évaluations","href":"/dashboard/evaluations.html?filter=draft"})
    actions.sort(key=lambda x: ({"critical":0,"warning":1,"info":2}[x["priority"]], -x["count"]))

    return {
        "scope": {"school_id": school_id, "academic_year_id": academic_year_id, "academic_period_id": academic_period_id},
        "kpis": {
            "active_students": len(students), "classes": len(classes),
            "school_average": school_average, "passing_rate": round(passing / len(averages) * 100, 1) if averages else None,
            "critical_students": risk_counts["critical"], "warning_students": risk_counts["warning"],
            "absences": absences, "unjustified_absences": unjustified, "lates": lates,
            "overdue_invoices": overdue, "total_due": total_due, "total_collected": total_collected,
            "collection_rate": round(total_collected / total_due * 100, 1) if total_due else None,
            "draft_grades": draft_grades,
        },
        "risk_distribution": {"critical": risk_counts["critical"], "warning": risk_counts["warning"], "normal": risk_counts["normal"]},
        "top_risks": top_risks,
        "actions": actions,
        "disclaimer": "Indicateurs d'aide à la décision pédagogique et administrative, sans valeur de diagnostic.",
    }
