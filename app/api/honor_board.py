from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
import csv
import io
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.academic import HonorBoardRule, HonorBoardEntry
from app.models.organization import AcademicPeriod, School
from app.schemas.honor_board import HonorBoardRuleCreate, HonorBoardRuleOut, HonorBoardGenerateRequest
from app.services.audit import log_action
from app.services.honor_board_engine import resolve_scope, calculate_entries
from app.services.honor_board_pdf import generate_honor_board_pdf
from app.services.authorization import user_has_permission

router = APIRouter(prefix="/api/honor-board", tags=["Tableau d'honneur"])


def _rule_access(rule: HonorBoardRule, current_user: User):
    if rule is None or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Règle introuvable")
    return rule


def _honor_scope_context(*, path_params, query_params, current_user, db):
    class_id = query_params.get("class_id")
    if class_id in (None, ""):
        # Une permission académique scoped ne doit jamais ouvrir silencieusement
        # tout l'établissement. Les responsables disposant d'un scope global
        # peuvent toujours appeler l'endpoint sans class_id.
        for code in ("administration.settings.modify", "administration.users.modify", "academic.report_cards.publish"):
            if user_has_permission(db, current_user, code, {}):
                return {}
        raise HTTPException(status_code=403, detail="Le périmètre de classe est obligatoire pour cette permission")
    return {"class_id": int(class_id)}


def _require_honor_scope(db: Session, current_user: User, permission_code: str, payload: HonorBoardGenerateRequest) -> None:
    context = {
        "class_id": payload.class_id,
        "level_id": payload.level_id,
        "stream_id": payload.stream_id,
    }
    if any(value is not None for value in context.values()):
        if user_has_permission(db, current_user, permission_code, context):
            return
    else:
        # Only a user carrying an unscoped/global permission may omit the scope.
        if user_has_permission(db, current_user, permission_code, {}):
            return
    raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{permission_code}' pour le périmètre demandé")


@router.get("/rules", response_model=list[HonorBoardRuleOut], dependencies=[Depends(require_permission("academic.grades.view"))])
def list_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(HonorBoardRule).filter(HonorBoardRule.school_id == current_user.school_id, HonorBoardRule.is_active.is_(True)).order_by(HonorBoardRule.name.asc()).all()


@router.post("/rules", response_model=HonorBoardRuleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_rule(payload: HonorBoardRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = HonorBoardRule(school_id=current_user.school_id, name=payload.name.strip(), criteria=payload.criteria or {})
    db.add(rule)
    db.commit(); db.refresh(rule)
    log_action(db, current_user.school_id, current_user, "honor_board.rule.create", "HonorBoardRule", rule.id, new_value=rule.name)
    return rule


@router.patch("/rules/{rule_id}", response_model=HonorBoardRuleOut, dependencies=[Depends(require_permission("administration.settings.modify"))])
def update_rule(rule_id: int, payload: HonorBoardRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = _rule_access(db.get(HonorBoardRule, rule_id), current_user) if db.get(HonorBoardRule, rule_id) else None
    if rule is None or not rule.is_active:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    existing_validated = db.query(HonorBoardEntry.id).filter(HonorBoardEntry.rule_id == rule.id, HonorBoardEntry.is_validated.is_(True)).first()
    if existing_validated:
        raise HTTPException(status_code=409, detail="Cette règle possède déjà des résultats validés et ne peut plus être modifiée.")
    rule.name = payload.name.strip(); rule.criteria = payload.criteria or {}
    db.commit(); db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def deactivate_rule(rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = db.get(HonorBoardRule, rule_id)
    if not rule or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if db.query(HonorBoardEntry.id).filter(HonorBoardEntry.rule_id == rule.id, HonorBoardEntry.is_validated.is_(True)).first():
        raise HTTPException(status_code=409, detail="Une règle avec un historique validé ne peut pas être supprimée.")
    rule.is_active = False
    db.commit()
    return {"status": "ok", "id": rule.id, "is_active": False}


@router.post("/{rule_id}/preview")
def preview(rule_id: int, payload: HonorBoardGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_honor_scope(db, current_user, "academic.grades.view", payload)
    rule = db.get(HonorBoardRule, rule_id)
    if not rule or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Règle introuvable")
    try:
        period, classes = resolve_scope(db, current_user.school_id, payload.academic_period_id, payload.class_id, payload.level_id, payload.stream_id)
        entries = calculate_entries(db, current_user.school_id, payload.academic_period_id, classes, rule.criteria or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"rule_id": rule.id, "rule_name": rule.name, "academic_period_id": period.id, "class_ids": [c.id for c in classes], "generated_count": len(entries), "entries": entries}


@router.post("/{rule_id}/generate")
def generate(rule_id: int, payload: HonorBoardGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_honor_scope(db, current_user, "academic.report_cards.generate", payload)
    rule = db.get(HonorBoardRule, rule_id)
    if not rule or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Règle introuvable")
    try:
        period, classes = resolve_scope(db, current_user.school_id, payload.academic_period_id, payload.class_id, payload.level_id, payload.stream_id)
        entries = calculate_entries(db, current_user.school_id, payload.academic_period_id, classes, rule.criteria or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if db.query(HonorBoardEntry.id).filter(HonorBoardEntry.rule_id == rule.id, HonorBoardEntry.academic_period_id == period.id, HonorBoardEntry.is_validated.is_(True)).first():
        raise HTTPException(status_code=409, detail="Des résultats validés existent déjà pour cette règle et cette période.")
    db.query(HonorBoardEntry).filter(HonorBoardEntry.rule_id == rule.id, HonorBoardEntry.academic_period_id == period.id, HonorBoardEntry.is_validated.is_(False)).delete(synchronize_session=False)
    for row in entries:
        db.add(HonorBoardEntry(
            rule_id=rule.id,
            student_id=row["student_id"],
            class_id=row["class_id"],
            academic_period_id=period.id,
            score=row["score"],
            rank=row["rank"],
            unjustified_absences=row.get("unjustified_absences", 0),
            is_validated=False,
        ))
    db.commit()
    log_action(db, current_user.school_id, current_user, "honor_board.generate", "HonorBoardRule", rule.id, new_value=f"period={period.id};count={len(entries)}")
    return {"status": "generated", "rule_id": rule.id, "academic_period_id": period.id, "count": len(entries), "entries": entries}


@router.get("/{rule_id}/entries", dependencies=[Depends(require_permission("academic.grades.view", context_builder=_honor_scope_context))])
def entries(rule_id: int, academic_period_id: int, class_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import Student, SchoolClass
    rule = _rule_access(db.get(HonorBoardRule, rule_id), current_user)
    period = db.get(AcademicPeriod, academic_period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Période introuvable")
    query = (
        db.query(HonorBoardEntry, Student, SchoolClass)
        .join(Student, Student.id == HonorBoardEntry.student_id)
        .join(SchoolClass, SchoolClass.id == HonorBoardEntry.class_id, isouter=True)
        .filter(
            HonorBoardEntry.rule_id == rule.id,
            HonorBoardEntry.academic_period_id == period.id,
            SchoolClass.school_id == current_user.school_id,
        )
    )
    if class_id is not None:
        query = query.filter(HonorBoardEntry.class_id == class_id)
    rows = query.order_by(HonorBoardEntry.rank.asc(), HonorBoardEntry.id.asc()).all()
    return [
        {
            "id": entry.id,
            "rule_id": entry.rule_id,
            "student_id": entry.student_id,
            "student_name": f"{student.last_name} {student.first_name}",
            "matricule": student.matricule,
            "class_id": entry.class_id or (cls.id if cls else None),
            "class_name": cls.name if cls else "",
            "academic_period_id": entry.academic_period_id,
            "score": float(entry.score or 0),
            "rank": entry.rank or 0,
            "is_validated": entry.is_validated,
            "unjustified_absences": entry.unjustified_absences,
        }
        for entry, student, cls in rows
    ]


@router.get("/{rule_id}/history", dependencies=[Depends(require_permission("academic.grades.view"))])
def history(rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = _rule_access(db.get(HonorBoardRule, rule_id), current_user)
    from sqlalchemy import func
    summary = (
        db.query(
            HonorBoardEntry.academic_period_id,
            func.count(HonorBoardEntry.id),
            func.max(HonorBoardEntry.created_at),
            func.max(HonorBoardEntry.is_validated.cast(int)),
        )
        .filter(HonorBoardEntry.rule_id == rule.id)
        .group_by(HonorBoardEntry.academic_period_id)
        .order_by(HonorBoardEntry.academic_period_id.desc())
        .all()
    )
    periods = {p.id: p for p in db.query(AcademicPeriod).filter(AcademicPeriod.id.in_([row[0] for row in summary])).all()} if summary else {}
    return [
        {
            "academic_period_id": period_id,
            "period_name": periods.get(period_id).name if periods.get(period_id) else "",
            "entry_count": int(count),
            "generated_at": created_at.isoformat() if created_at else None,
            "is_validated": bool(validated),
        }
        for period_id, count, created_at, validated in summary
    ]


@router.post("/entries/{entry_id}/validate", dependencies=[Depends(require_permission("academic.report_cards.publish"))])
def validate_entry(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.get(HonorBoardEntry, entry_id)
    rule = db.get(HonorBoardRule, entry.rule_id) if entry else None
    if not entry or not rule or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    entry.is_validated = True
    entry.validated_at = datetime.now(timezone.utc)
    entry.validated_by_id = current_user.id
    db.commit()
    log_action(db, current_user.school_id, current_user, "honor_board.validate", "HonorBoardEntry", entry.id)
    return {"status": "validated", "id": entry.id}


@router.post("/{rule_id}/validate", dependencies=[Depends(require_permission("academic.report_cards.publish"))])
def validate_rule(rule_id: int, academic_period_id: int, class_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = _rule_access(db.get(HonorBoardRule, rule_id), current_user)
    query = db.query(HonorBoardEntry).filter(
        HonorBoardEntry.rule_id == rule.id,
        HonorBoardEntry.academic_period_id == academic_period_id,
        HonorBoardEntry.is_validated.is_(False),
    )
    if class_id is not None:
        query = query.filter(HonorBoardEntry.class_id == class_id)
    entries = query.all()
    if not entries:
        raise HTTPException(status_code=404, detail="Aucun résultat non validé pour cette période.")
    now = datetime.now(timezone.utc)
    for entry in entries:
        entry.is_validated = True
        entry.validated_at = now
        entry.validated_by_id = current_user.id
    db.commit()
    log_action(db, current_user.school_id, current_user, "honor_board.validate_batch", "HonorBoardRule", rule.id, new_value=f"period={academic_period_id};count={len(entries)}")
    return {"status": "validated", "rule_id": rule.id, "academic_period_id": academic_period_id, "count": len(entries)}


@router.get("/{rule_id}/csv", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def export_csv(rule_id: int, academic_period_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = _rule_access(db.get(HonorBoardRule, rule_id), current_user)
    period = db.get(AcademicPeriod, academic_period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Période introuvable")
    from app.models.students import Student, SchoolClass
    rows = (
        db.query(HonorBoardEntry, Student, SchoolClass)
        .join(Student, Student.id == HonorBoardEntry.student_id)
        .join(SchoolClass, SchoolClass.id == HonorBoardEntry.class_id, isouter=True)
        .filter(
            HonorBoardEntry.rule_id == rule.id,
            HonorBoardEntry.academic_period_id == period.id,
            (SchoolClass.school_id == current_user.school_id) | (HonorBoardEntry.class_id.is_(None)),
        )
        .order_by(HonorBoardEntry.rank.asc(), HonorBoardEntry.id.asc())
        .all()
    )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["rank", "matricule", "student", "class", "score", "validated"])
    for entry, student, cls in rows:
        writer.writerow([entry.rank or 0, student.matricule, f"{student.last_name} {student.first_name}", cls.name if cls else "", f"{float(entry.score or 0):.2f}", "yes" if entry.is_validated else "no"])
    return Response(content="\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="honor-board-{rule.id}-{period.id}.csv"'})


@router.get("/{rule_id}/pdf", dependencies=[Depends(require_permission("academic.report_cards.generate"))])
def export_pdf(rule_id: int, academic_period_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = db.get(HonorBoardRule, rule_id)
    if not rule or (rule.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Règle introuvable")
    period = db.get(AcademicPeriod, academic_period_id)
    school = db.get(School, rule.school_id)
    if not period or not school:
        raise HTTPException(status_code=404, detail="Données introuvables")
    from app.models.students import Student, SchoolClass
    query = (
        db.query(HonorBoardEntry, Student, SchoolClass)
        .join(Student, Student.id == HonorBoardEntry.student_id)
        .join(SchoolClass, SchoolClass.id == HonorBoardEntry.class_id, isouter=True)
        .filter(
            HonorBoardEntry.rule_id == rule.id,
            HonorBoardEntry.academic_period_id == period.id,
            (SchoolClass.school_id == current_user.school_id) | (HonorBoardEntry.class_id.is_(None)),
        )
        .order_by(HonorBoardEntry.rank.asc(), HonorBoardEntry.id.asc())
        .all()
    )
    entries_data = [
        {"rank": row.rank or 0, "matricule": student.matricule, "student_name": f"{student.last_name} {student.first_name}", "class_name": cls.name if cls else "", "score": float(row.score or 0), "unjustified_absences": row.unjustified_absences}
        for row, student, cls in query
    ]
    pdf = generate_honor_board_pdf(school.name, period.name, rule.name, entries_data, language="en" if school.language == "en" else "fr")
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="honor-board-{rule.id}-{period.id}.pdf"'})
