"""Pilot deployment readiness and first-school operational checks."""
from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.security import User, UserPost
from app.models.students import Student, SchoolClass, ClassMembership, Guardian
from app.models.finance import Invoice, Payment
from app.models.onboarding import SchoolOnboarding
from app.services.backup import create_backup, list_backups
from app.services.onboarding import get_or_create, _refresh_checklist


def _count(db: Session, model, school_id: int) -> int:
    if hasattr(model, "school_id"):
        return db.query(model).filter(model.school_id == school_id).count()
    return 0


def pilot_readiness(db: Session, school_id: int) -> dict:
    school = db.get(School, school_id)
    if not school:
        raise ValueError("Établissement introuvable")
    onboarding = get_or_create(db, school_id)
    _refresh_checklist(db, onboarding)
    year = db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True)).first()
    periods = db.query(AcademicPeriod).filter(AcademicPeriod.academic_year_id == year.id).count() if year else 0
    users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
    classes = db.query(SchoolClass).filter(SchoolClass.school_id == school_id, SchoolClass.is_active.is_(True)).count()
    students = db.query(Student).filter(Student.school_id == school_id, Student.is_active.is_(True)).count()
    guardians = db.query(Guardian).filter(Guardian.school_id == school_id, Guardian.is_active.is_(True)).count()
    memberships = db.query(ClassMembership).join(Student, ClassMembership.student_id == Student.id).filter(Student.school_id == school_id).count()
    invoices = db.query(Invoice).join(Student, Invoice.student_id == Student.id).filter(Student.school_id == school_id).count()
    payments = db.query(Payment).join(Student, Payment.student_id == Student.id).filter(Student.school_id == school_id).count()
    backups = list_backups()
    checks = {
        "school_configured": bool(school.name and school.currency),
        "academic_year": bool(year),
        "academic_periods": periods >= 1,
        "admin_user": users >= 1,
        "rbac_assigned": db.query(UserPost).join(User).filter(User.school_id == school_id).count() >= 1,
        "onboarding_complete": bool(onboarding.is_completed),
        "backup_available": bool(backups),
        "students_ready": students >= 0,
        "classes_ready": classes >= 0,
    }
    required = ("school_configured", "academic_year", "academic_periods", "admin_user", "rbac_assigned", "onboarding_complete")
    ready = all(checks[k] for k in required)
    return {
        "school_id": school_id,
        "ready_for_pilot": ready,
        "checks": checks,
        "required_checks": list(required),
        "onboarding": {
            "status": onboarding.status,
            "current_step": onboarding.current_step,
            "completed": onboarding.is_completed,
            "checklist": onboarding.checklist,
        },
        "counts": {
            "users": users,
            "classes": classes,
            "students": students,
            "guardians": guardians,
            "memberships": memberships,
            "invoices": invoices,
            "payments": payments,
            "backups": len(backups),
        },
        "current_year": {
            "id": year.id,
            "label": year.label,
            "periods": periods,
        } if year else None,
        "next_actions": [
            label for key, label in [
                ("school_configured", "Compléter les informations de l'établissement"),
                ("academic_year", "Configurer l'année scolaire"),
                ("academic_periods", "Créer les périodes scolaires"),
                ("admin_user", "Créer/valider le compte administrateur"),
                ("rbac_assigned", "Attribuer un poste opérationnel"),
                ("onboarding_complete", "Terminer l'assistant d'installation"),
                ("backup_available", "Créer une première sauvegarde"),
            ] if not checks[key]
        ],
    }


def prepare_pilot(db: Session, school_id: int, actor: User, year_label: str, start: date, end: date, period_count: int = 3) -> dict:
    if end <= start:
        raise ValueError("La date de fin doit être postérieure à la date de début")
    from app.services.onboarding import bootstrap
    bootstrap(db, school_id, actor, year_label, start, end, period_count)
    # Une sauvegarde initiale est une barrière opérationnelle avant les premières données réelles.
    backup = create_backup()
    result = pilot_readiness(db, school_id)
    result["initial_backup"] = {"name": backup.name, "size": backup.stat().st_size}
    return result
