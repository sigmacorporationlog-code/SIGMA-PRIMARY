"""Centre d'actions SIGMA Intelligence.

V4.9 : les actions sont proposées et validées explicitement. Aucune action
réelle (envoi, modification, paiement, suppression) n'est exécutée par ce
module. Les exécuteurs spécialisés seront ajoutés ultérieurement et devront
repasser par une validation d'autorisation et une trace d'audit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ai_actions import AIActionProposal
from app.models.ai import AIInteraction
from app.models.students import Guardian, Student, StudentGuardian
from app.models.finance import Invoice
from app.models.organization import School
from app.services.communication_engine import create_delivery
from app.services.notification import create_notification
from app.services.pdf_engine import generate_students_list_pdf
from app.core.config import settings
from app.core.paths import data_dir
from pathlib import Path
import hashlib
import json
from app.models.security import User
from app.services.audit import log_action
from app.services.authorization import user_has_permission

AI_PERMISSION = "administration.ai.use"
AI_EXECUTE_PERMISSION = "administration.ai.execute"
ALLOWED_ACTION_TYPES = {
    "communication_draft",
    "finance_reminder",
    "pedagogy_remediation",
    "report_generation",
}
VALID_STATUSES = {"proposed", "approved", "rejected", "expired", "executed"}


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    return current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current


def _expire_if_needed(proposal: AIActionProposal) -> bool:
    if proposal.status == "proposed" and proposal.expires_at and _utc_now(proposal.expires_at) <= _utc_now():
        proposal.status = "expired"
        return True
    return False


def _assert_access(proposal: AIActionProposal, user: User) -> None:
    if proposal.school_id != user.school_id and not user.is_superadmin:
        raise ValueError("Proposition introuvable dans le périmètre autorisé")


def create_proposal(
    db: Session,
    user: User,
    *,
    action_type: str,
    title: str,
    description: str | None = None,
    payload: dict | None = None,
    ai_interaction_id: int | None = None,
    expires_in_minutes: int = 60,
) -> AIActionProposal:
    if not user_has_permission(db, user, AI_PERMISSION):
        raise PermissionError(AI_PERMISSION)
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError("Type d'action IA non autorisé")
    if ai_interaction_id is not None:
        interaction = db.get(AIInteraction, ai_interaction_id)
        if not interaction or (interaction.school_id != user.school_id and not user.is_superadmin):
            raise ValueError("Interaction IA introuvable dans le périmètre autorisé")
    if not title.strip() or len(title) > 255:
        raise ValueError("Le titre de l'action est obligatoire et limité à 255 caractères")
    if expires_in_minutes < 5 or expires_in_minutes > 10080:
        raise ValueError("La durée d'expiration doit être comprise entre 5 minutes et 7 jours")

    now = datetime.now(timezone.utc)
    execution_key = hashlib.sha256(f"{user.school_id}:{user.id}:{now.timestamp()}:{action_type}:{title.strip()}".encode()).hexdigest()
    proposal = AIActionProposal(
        school_id=user.school_id,
        created_by_user_id=user.id,
        ai_interaction_id=ai_interaction_id,
        action_type=action_type,
        title=title.strip(),
        description=(description or "").strip() or None,
        payload_json=payload or {},
        status="proposed",
        created_at=now,
        expires_at=now + timedelta(minutes=expires_in_minutes),
        result_json={},
        execution_key=execution_key,
    )
    db.add(proposal)
    db.flush()
    log_action(
        db, user.school_id, user, "ai.action.propose", "AIActionProposal", str(proposal.id),
        new_value=f"{action_type}:{title.strip()}", commit=False,
    )
    db.commit()
    db.refresh(proposal)
    return proposal


def list_proposals(db: Session, user: User, status: str | None = None, limit: int = 100) -> list[AIActionProposal]:
    if not user_has_permission(db, user, AI_PERMISSION):
        raise PermissionError(AI_PERMISSION)
    query = db.query(AIActionProposal)
    if not user.is_superadmin:
        query = query.filter(AIActionProposal.school_id == user.school_id)
    if status:
        if status not in VALID_STATUSES:
            raise ValueError("Statut de proposition IA invalide")
        query = query.filter(AIActionProposal.status == status)
    proposals = query.order_by(AIActionProposal.created_at.desc()).limit(min(limit, 200)).all()
    changed = False
    for proposal in proposals:
        changed = _expire_if_needed(proposal) or changed
    if changed:
        db.commit()
    return proposals


def control_center(db: Session, user: User, limit: int = 20) -> dict:
    """Vue agrégée du centre de contrôle IA, limitée au périmètre de l'utilisateur."""
    if not user_has_permission(db, user, AI_PERMISSION):
        raise PermissionError(AI_PERMISSION)
    query = db.query(AIActionProposal)
    if not user.is_superadmin:
        query = query.filter(AIActionProposal.school_id == user.school_id)
    all_proposals = query.all()
    changed = False
    counts = {status: 0 for status in VALID_STATUSES}
    for proposal in all_proposals:
        changed = _expire_if_needed(proposal) or changed
        counts[proposal.status] = counts.get(proposal.status, 0) + 1
    proposals = sorted(all_proposals, key=lambda item: item.created_at or datetime.min, reverse=True)[:min(max(limit, 1), 100)]
    if changed:
        db.commit()
    return {
        "scope": {"school_id": None if user.is_superadmin else user.school_id, "superadmin": bool(user.is_superadmin)},
        "counts": counts,
        "execution": {
            "enabled": bool(settings.AI_ACTION_EXECUTION_ENABLED),
            "max_recipients": int(settings.AI_ACTION_MAX_RECIPIENTS),
            "can_execute": bool(user_has_permission(db, user, AI_EXECUTE_PERMISSION)),
        },
        "proposals": proposals,
    }


def approve(db: Session, user: User, proposal_id: int) -> AIActionProposal:
    if not user_has_permission(db, user, AI_EXECUTE_PERMISSION):
        raise PermissionError(AI_EXECUTE_PERMISSION)
        raise PermissionError(AI_PERMISSION)
    proposal = db.get(AIActionProposal, proposal_id)
    if not proposal:
        raise ValueError("Proposition IA introuvable")
    _assert_access(proposal, user)
    if _expire_if_needed(proposal):
        db.commit()
    if proposal.status != "proposed":
        raise ValueError(f"La proposition ne peut plus être validée (statut={proposal.status})")
    now = datetime.now(timezone.utc)
    proposal.status = "approved"
    proposal.approved_by_user_id = user.id
    proposal.approved_at = now
    db.flush()
    log_action(db, user.school_id, user, "ai.action.approve", "AIActionProposal", str(proposal.id), commit=False)
    db.commit()
    db.refresh(proposal)
    return proposal


def reject(db: Session, user: User, proposal_id: int, reason: str | None = None) -> AIActionProposal:
    if not user_has_permission(db, user, AI_EXECUTE_PERMISSION):
        raise PermissionError(AI_EXECUTE_PERMISSION)
        raise PermissionError(AI_PERMISSION)
    proposal = db.get(AIActionProposal, proposal_id)
    if not proposal:
        raise ValueError("Proposition IA introuvable")
    _assert_access(proposal, user)
    if _expire_if_needed(proposal):
        db.commit()
    if proposal.status != "proposed":
        raise ValueError(f"La proposition ne peut plus être rejetée (statut={proposal.status})")
    proposal.status = "rejected"
    proposal.rejected_at = datetime.now(timezone.utc)
    proposal.rejection_reason = (reason or "").strip() or None
    db.flush()
    log_action(db, user.school_id, user, "ai.action.reject", "AIActionProposal", str(proposal.id), new_value=proposal.rejection_reason, commit=False)
    db.commit()
    db.refresh(proposal)
    return proposal



def _assert_execute(db: Session, user: User, proposal: AIActionProposal) -> None:
    if not user_has_permission(db, user, AI_EXECUTE_PERMISSION):
        raise PermissionError(AI_EXECUTE_PERMISSION)
    _assert_access(proposal, user)
    if not settings.AI_ACTION_EXECUTION_ENABLED:
        raise RuntimeError("L'exécution des actions IA est désactivée par la configuration système")


def _school_name(db: Session, school_id: int) -> str:
    school = db.get(School, school_id)
    return school.name if school else "Établissement SIGMA"


def _execute_communication(db: Session, user: User, proposal: AIActionProposal) -> dict:
    payload = proposal.payload_json or {}
    guardian_ids = payload.get("guardian_ids") or []
    body = str(payload.get("body") or "").strip()
    title = str(payload.get("title") or proposal.title).strip()
    channel = str(payload.get("channel") or "auto")
    if not body:
        raise ValueError("Le message à envoyer est obligatoire")
    if not isinstance(guardian_ids, list) or not guardian_ids:
        raise ValueError("Aucun destinataire n'est défini")
    if len(guardian_ids) > settings.AI_ACTION_MAX_RECIPIENTS:
        raise ValueError("Le nombre de destinataires dépasse la limite de sécurité")
    guardians = db.query(Guardian).filter(Guardian.school_id == proposal.school_id, Guardian.id.in_(guardian_ids)).all()
    if len(guardians) != len(set(guardian_ids)):
        raise ValueError("Un ou plusieurs destinataires ne sont pas dans l'établissement autorisé")
    sent = failed = 0
    deliveries = []
    for guardian in guardians:
        delivery = create_delivery(db, school_id=proposal.school_id, guardian_id=guardian.id,
                                   body=body, channel=channel, title=title, send_now=True)
        deliveries.append(delivery.id)
        if delivery.status in {"sent", "delivered"}:
            sent += 1
        else:
            failed += 1
    return {"type": "communication", "total": len(guardians), "sent": sent, "failed": failed, "delivery_ids": deliveries}


def _execute_finance_reminder(db: Session, user: User, proposal: AIActionProposal) -> dict:
    payload = proposal.payload_json or {}
    invoice_ids = payload.get("invoice_ids") or []
    body = str(payload.get("body") or "").strip()
    title = str(payload.get("title") or "Rappel de paiement SIGMA").strip()
    channel = str(payload.get("channel") or "auto")
    if not body or not invoice_ids:
        raise ValueError("Les factures et le message de relance sont obligatoires")
    if len(invoice_ids) > settings.AI_ACTION_MAX_RECIPIENTS:
        raise ValueError("Le nombre de factures dépasse la limite de sécurité")
    invoices = db.query(Invoice).filter(Invoice.id.in_(invoice_ids), Invoice.school_id == proposal.school_id).all()
    student_ids = {i.student_id for i in invoices}
    students = {s.id: s for s in db.query(Student).filter(Student.school_id == proposal.school_id, Student.id.in_(student_ids)).all()}
    if len(students) != len(student_ids):
        raise ValueError("Une facture cible un élève hors établissement")
    sent = failed = 0
    delivery_ids = []
    for invoice in invoices:
        links = db.query(StudentGuardian).filter(StudentGuardian.student_id == invoice.student_id).all()
        guardians = [db.get(Guardian, link.guardian_id) for link in links]
        guardians = [g for g in guardians if g and g.school_id == proposal.school_id]
        if not guardians:
            failed += 1
            continue
        guardian = next((g for g in guardians if g.phone or g.user_id), guardians[0])
        delivery = create_delivery(db, school_id=proposal.school_id, guardian_id=guardian.id,
                                   student_id=invoice.student_id, body=body, channel=channel,
                                   title=title, send_now=True)
        delivery_ids.append(delivery.id)
        if delivery.status in {"sent", "delivered"}:
            sent += 1
        else:
            failed += 1
    return {"type": "finance_reminder", "invoices": len(invoices), "sent": sent, "failed": failed, "delivery_ids": delivery_ids}


def _execute_pedagogy(db: Session, user: User, proposal: AIActionProposal) -> dict:
    payload = proposal.payload_json or {}
    student_ids = payload.get("student_ids") or []
    message = str(payload.get("message") or proposal.description or "Une action pédagogique proposée par SIGMA Intelligence nécessite votre attention.").strip()
    if not student_ids:
        raise ValueError("Aucun élève n'est défini pour la remédiation")
    if len(student_ids) > settings.AI_ACTION_MAX_RECIPIENTS:
        raise ValueError("Le nombre d'élèves dépasse la limite de sécurité")
    students = db.query(Student).filter(Student.school_id == proposal.school_id, Student.id.in_(student_ids)).all()
    if len(students) != len(set(student_ids)):
        raise ValueError("Un ou plusieurs élèves ne sont pas dans l'établissement autorisé")
    notification = create_notification(db, school_id=proposal.school_id, user_id=user.id,
        type="ai.pedagogy.remediation", title=proposal.title,
        body=message, data={"student_ids": student_ids, "proposal_id": proposal.id}, commit=False)
    db.flush()
    return {"type": "pedagogy_remediation", "students": len(students), "notification_id": notification.id}


def _execute_report(db: Session, user: User, proposal: AIActionProposal) -> dict:
    students = db.query(Student).filter(Student.school_id == proposal.school_id, Student.status == "active").order_by(Student.last_name, Student.first_name).all()
    rows = [{"matricule": s.matricule, "last_name": s.last_name, "first_name": s.first_name, "sex": s.sex, "status": s.status, "class_name": ""} for s in students]
    pdf = generate_students_list_pdf(_school_name(db, proposal.school_id), rows)
    reports_dir = data_dir() / "media" / "ai_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"ai-report-{proposal.id}.pdf"
    path.write_bytes(pdf)
    return {"type": "report_generation", "file_path": str(path), "students": len(students), "size_bytes": len(pdf)}


def execute(db: Session, user: User, proposal_id: int) -> AIActionProposal:
    proposal = db.get(AIActionProposal, proposal_id)
    if not proposal:
        raise ValueError("Proposition IA introuvable")
    _assert_execute(db, user, proposal)
    if proposal.status == "executed":
        return proposal
    if proposal.status != "approved":
        raise ValueError(f"La proposition doit être approuvée avant exécution (statut={proposal.status})")
    if proposal.expires_at and _utc_now(proposal.expires_at) <= _utc_now():
        proposal.status = "expired"
        db.commit()
        raise ValueError("La proposition IA a expiré")
    if proposal.execution_key and proposal.result_json and proposal.result_json.get("execution_key") == proposal.execution_key:
        proposal.status = "executed"
        return proposal
    executors = {
        "communication_draft": _execute_communication,
        "finance_reminder": _execute_finance_reminder,
        "pedagogy_remediation": _execute_pedagogy,
        "report_generation": _execute_report,
    }
    executor = executors.get(proposal.action_type)
    if not executor:
        raise ValueError("Type d'action IA sans exécuteur")
    try:
        result = executor(db, user, proposal)
        result["execution_key"] = proposal.execution_key
        result["executed_by_user_id"] = user.id
        result["executed_at"] = datetime.now(timezone.utc).isoformat()
        proposal.result_json = result
        proposal.status = "executed"
        proposal.executed_at = datetime.now(timezone.utc)
        db.flush()
        log_action(db, proposal.school_id, user, "ai.action.execute", "AIActionProposal", str(proposal.id), new_value=json.dumps(result, ensure_ascii=False)[:4000], commit=False)
        db.commit()
        db.refresh(proposal)
        return proposal
    except Exception:
        db.rollback()
        raise
