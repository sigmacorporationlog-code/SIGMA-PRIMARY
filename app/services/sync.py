"""Règles déterministes du protocole de synchronisation SIGMA."""

from dataclasses import dataclass


SYNC_STATUSES = {"pending", "applied", "conflict", "failed"}
OPERATION_TYPES = {"create", "update", "delete", "transition"}


@dataclass(frozen=True)
class ApplyDecision:
    status: str
    new_version: int
    error: str | None = None


def decide_apply(base_version: int, current_version: int) -> ApplyDecision:
    """Autorise une opération seulement si sa base correspond à la version serveur."""
    if base_version != current_version:
        return ApplyDecision(
            status="conflict",
            new_version=current_version,
            error=f"Conflit de version: client={base_version}, serveur={current_version}",
        )
    return ApplyDecision(status="applied", new_version=current_version + 1)


def validate_operation_type(operation_type: str) -> str:
    if operation_type not in OPERATION_TYPES:
        raise ValueError(f"Type d'opération invalide: {operation_type}")
    return operation_type


from datetime import date
from app.models.students import Student, Guardian, StudentGuardian, ClassMembership, SchoolClass
from app.models.academic import Grade, Assessment, GradeAudit, GRADE_STATES
from app.models.evaluation import EvaluationPeriodClosure, EvaluationResult, EvaluationActivity
from app.models.organization import AcademicPeriod
from app.models.sync import SyncEntityIdentity
from app.services.cloud import enforce_subscription_capacity, SubscriptionError


ENTITY_HANDLERS = {
    "student": Student,
    "guardian": Guardian,
    "student_guardian": StudentGuardian,
    "class_membership": ClassMembership,
    "grade": Grade,
    "evaluation_result": EvaluationResult,
}

ALLOWED_FIELDS = {
    "student": {"matricule", "first_name", "last_name", "birth_date", "birth_place", "sex", "nationality", "address", "status"},
    "guardian": {"first_name", "last_name", "relationship_type", "phone", "email", "address", "can_pick_up_child"},
    "student_guardian": {"student_entity_id", "student_id", "guardian_entity_id", "guardian_id", "is_primary_contact"},
    "class_membership": {"student_entity_id", "student_id", "class_id", "academic_year_id", "enrolled_at", "left_at", "enrollment_type"},
    "grade": {"assessment_id", "student_entity_id", "student_id", "score", "is_absent", "state", "comment"},
    "evaluation_result": {"activity_id", "student_entity_id", "student_id", "score", "max_score", "is_absent", "observation", "strengths", "needs_support"},
}


def _coerce_value(entity_type: str, field: str, value):
    if entity_type == "student" and field == "birth_date" and value:
        return date.fromisoformat(value) if isinstance(value, str) else value
    if entity_type == "class_membership" and field in {"enrolled_at", "left_at"} and value:
        return date.fromisoformat(value) if isinstance(value, str) else value
    if entity_type == "guardian" and field == "can_pick_up_child":
        if not isinstance(value, bool):
            raise ValueError("can_pick_up_child doit être booléen")
    return value


def _resolve_server_id(db, operation):
    """Résout un ID serveur ou une identité client déjà synchronisée."""
    try:
        return int(operation.entity_id)
    except (TypeError, ValueError):
        identity = db.query(SyncEntityIdentity).filter(
            SyncEntityIdentity.school_id == operation.school_id,
            SyncEntityIdentity.entity_type == operation.entity_type,
            SyncEntityIdentity.client_entity_id == operation.entity_id,
        ).first()
        if identity is None:
            return None
        return identity.server_entity_id



def _evaluation_result_context(db, result):
    activity = db.query(EvaluationActivity).filter(EvaluationActivity.id == result.activity_id).first()
    if activity is None:
        raise ValueError("Activité d'évaluation introuvable")
    school_class = db.query(SchoolClass).filter(SchoolClass.id == activity.class_id).first()
    if school_class is None:
        raise ValueError("Classe de l'activité introuvable")
    if not db.query(Student).filter(Student.id == result.student_id, Student.school_id == school_class.school_id).first():
        raise ValueError("Élève hors établissement")
    closure = db.query(EvaluationPeriodClosure).filter(
        EvaluationPeriodClosure.class_id == activity.class_id,
        EvaluationPeriodClosure.academic_period_id == activity.academic_period_id,
    ).first()
    if closure is not None and closure.status in {"closed", "published"}:
        raise ValueError("Période clôturée/publiée: modification du résultat interdite")
    period = db.query(AcademicPeriod).filter(AcademicPeriod.id == activity.academic_period_id).first()
    if period is not None and (period.is_locked or not period.is_grade_entry_open):
        raise ValueError("Saisie des évaluations fermée pour cette période")
    return activity, school_class


def _validate_evaluation_result_payload(db, operation):
    payload = operation.payload
    if not payload.get("activity_id"):
        raise ValueError("activity_id est obligatoire pour un résultat d'évaluation")
    activity = db.query(EvaluationActivity).filter(EvaluationActivity.id == payload["activity_id"]).first()
    if activity is None:
        raise ValueError("Activité d'évaluation introuvable")
    school_class = db.query(SchoolClass).filter(SchoolClass.id == activity.class_id, SchoolClass.school_id == operation.school_id).first()
    if school_class is None:
        raise ValueError("Activité hors établissement")
    period = db.query(AcademicPeriod).filter(AcademicPeriod.id == activity.academic_period_id).first()
    if period is not None and (period.is_locked or not period.is_grade_entry_open):
        raise ValueError("Saisie des évaluations fermée pour cette période")
    closure = db.query(EvaluationPeriodClosure).filter(
        EvaluationPeriodClosure.class_id == activity.class_id,
        EvaluationPeriodClosure.academic_period_id == activity.academic_period_id,
    ).first()
    if closure is not None and closure.status in {"closed", "published"}:
        raise ValueError("Période clôturée/publiée: création de résultat interdite")
    student_ref = payload.get("student_entity_id") or payload.get("student_id")
    if not student_ref:
        raise ValueError("student_entity_id est obligatoire")
    try:
        student_id = int(student_ref)
    except (TypeError, ValueError):
        identity = db.query(SyncEntityIdentity).filter(
            SyncEntityIdentity.school_id == operation.school_id,
            SyncEntityIdentity.entity_type == "student",
            SyncEntityIdentity.client_entity_id == str(student_ref),
        ).first()
        if identity is None:
            raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
        student_id = identity.server_entity_id
    membership = db.query(ClassMembership).filter(
        ClassMembership.student_id == student_id, ClassMembership.class_id == activity.class_id,
        ClassMembership.academic_year_id == school_class.academic_year_id, ClassMembership.left_at.is_(None),
    ).first()
    if membership is None:
        raise ValueError("L'élève n'est pas inscrit dans la classe de l'activité")
    score = payload.get("score")
    max_score = payload.get("max_score", activity.max_score)
    if score is not None and (max_score is None or float(max_score) <= 0):
        raise ValueError("Un score nécessite un barème maximal positif")
    if score is not None and (float(score) < 0 or float(score) > float(max_score)):
        raise ValueError("Le score doit être compris entre 0 et le barème maximal")
    if payload.get("is_absent") and score is not None:
        raise ValueError("Un élève absent ne peut pas avoir de score")
    return student_id, activity

def _grade_period_is_closed(db, grade):
    """Refuse toute mutation synchronisée après clôture de la période de la note."""
    assessment = db.query(Assessment).filter(Assessment.id == grade.assessment_id).first()
    if assessment is None:
        raise ValueError("Évaluation introuvable pour cette note")
    closure = db.query(EvaluationPeriodClosure).filter(
        EvaluationPeriodClosure.class_id == assessment.class_id,
        EvaluationPeriodClosure.academic_period_id == assessment.academic_period_id,
    ).first()
    if closure is not None and closure.status in {"closed", "published"}:
        raise ValueError("Période clôturée/publiée: modification de note interdite")
    period = db.query(AcademicPeriod).filter(AcademicPeriod.id == assessment.academic_period_id).first()
    if period is not None and (period.is_locked or not period.is_grade_entry_open):
        raise ValueError("Saisie des notes fermée pour cette période")
    return assessment


def _validate_grade_transition(current_state: str, target_state: str) -> None:
    if current_state not in GRADE_STATES or target_state not in GRADE_STATES:
        raise ValueError(f"État de note invalide: {current_state} -> {target_state}")
    current_index = GRADE_STATES.index(current_state)
    target_index = GRADE_STATES.index(target_state)
    if target_index != current_index + 1:
        raise ValueError(f"Transition interdite: {current_state} -> {target_state}")


def _create_business_entity(db, operation):
    model = ENTITY_HANDLERS.get(operation.entity_type)
    if model is None:
        raise ValueError(f"Entité non synchronisable: {operation.entity_type}")
    if operation.entity_type == "class_membership":
        payload = operation.payload
        if not payload.get("class_id") or not payload.get("academic_year_id"):
            raise ValueError("class_id et academic_year_id sont obligatoires pour une inscription")
        student_ref = payload.get("student_entity_id") or payload.get("student_id")
        if not student_ref:
            raise ValueError("student_entity_id est obligatoire pour une inscription offline")
        try:
            student_id = int(student_ref)
        except (TypeError, ValueError):
            identity = db.query(SyncEntityIdentity).filter(
                SyncEntityIdentity.school_id == operation.school_id,
                SyncEntityIdentity.entity_type == "student",
                SyncEntityIdentity.client_entity_id == str(student_ref),
            ).first()
            if identity is None:
                raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
            student_id = identity.server_entity_id
        student = db.query(Student).filter(Student.id == student_id, Student.school_id == operation.school_id).first()
        if student is None:
            raise ValueError("Élève introuvable dans cet établissement")
        school_class = db.query(SchoolClass).filter(
            SchoolClass.id == payload["class_id"],
            SchoolClass.school_id == operation.school_id,
            SchoolClass.academic_year_id == payload["academic_year_id"],
        ).first()
        if school_class is None:
            raise ValueError("Classe/année scolaire invalide pour cet établissement")
        existing = db.query(ClassMembership).filter(
            ClassMembership.student_id == student_id,
            ClassMembership.academic_year_id == payload["academic_year_id"],
            ClassMembership.left_at.is_(None),
        ).first()
        if existing is not None:
            raise ValueError("Conflit de création: l'élève possède déjà une inscription active pour cette année")
    elif operation.entity_type == "evaluation_result":
        student_id, activity = _validate_evaluation_result_payload(db, operation)
        if db.query(EvaluationResult).filter(EvaluationResult.activity_id == activity.id, EvaluationResult.student_id == student_id).first() is not None:
            raise ValueError("Conflit de création: un résultat existe déjà pour cet élève et cette activité")
    elif operation.entity_type == "grade":
        payload = operation.payload
        if not payload.get("assessment_id"):
            raise ValueError("assessment_id est obligatoire pour une note")
        assessment = db.query(Assessment).filter(Assessment.id == payload["assessment_id"]).first()
        if assessment is None:
            raise ValueError("Évaluation introuvable")
        closure = db.query(EvaluationPeriodClosure).filter(
            EvaluationPeriodClosure.class_id == assessment.class_id,
            EvaluationPeriodClosure.academic_period_id == assessment.academic_period_id,
        ).first()
        if closure is not None and closure.status in {"closed", "published"}:
            raise ValueError("Période clôturée/publiée: création de note interdite")
        period = db.query(AcademicPeriod).filter(AcademicPeriod.id == assessment.academic_period_id).first()
        if period is not None and (period.is_locked or not period.is_grade_entry_open):
            raise ValueError("Saisie des notes fermée pour cette période")
        student_ref = payload.get("student_entity_id") or payload.get("student_id")
        if not student_ref:
            raise ValueError("student_entity_id est obligatoire pour une note offline")
        try:
            student_id = int(student_ref)
        except (TypeError, ValueError):
            identity = db.query(SyncEntityIdentity).filter(
                SyncEntityIdentity.school_id == operation.school_id,
                SyncEntityIdentity.entity_type == "student",
                SyncEntityIdentity.client_entity_id == str(student_ref),
            ).first()
            if identity is None:
                raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
            student_id = identity.server_entity_id
        student = db.query(Student).filter(Student.id == student_id, Student.school_id == operation.school_id).first()
        school_class = db.query(SchoolClass).filter(SchoolClass.id == assessment.class_id, SchoolClass.school_id == operation.school_id).first()
        if student is None or school_class is None:
            raise ValueError("Élève ou classe introuvable dans cet établissement")
        membership = db.query(ClassMembership).filter(
            ClassMembership.student_id == student_id,
            ClassMembership.class_id == assessment.class_id,
            ClassMembership.academic_year_id == school_class.academic_year_id,
            ClassMembership.left_at.is_(None),
        ).first()
        if membership is None:
            raise ValueError("L'élève n'est pas inscrit dans la classe de l'évaluation")
        existing = db.query(Grade).filter(Grade.assessment_id == assessment.id, Grade.student_id == student_id).first()
        if existing is not None:
            raise ValueError("Conflit de création: une note existe déjà pour cet élève et cette évaluation")
        if payload.get("state", "draft") not in {"draft", "submitted"}:
            raise ValueError("Une note créée offline doit rester en draft ou submitted")
    elif operation.entity_type == "student":
        try:
            enforce_subscription_capacity(db, operation.school_id, "students")
        except SubscriptionError as exc:
            raise ValueError(str(exc)) from exc
        required = {"matricule", "first_name", "last_name"}
        missing = required - set(operation.payload)
        if missing:
            raise ValueError(f"Champs obligatoires manquants: {', '.join(sorted(missing))}")
        existing = db.query(Student).filter(
            Student.school_id == operation.school_id,
            Student.matricule == operation.payload["matricule"],
        ).first()
        if existing is not None:
            raise ValueError("Conflit de création: matricule déjà utilisé dans cet établissement")
    elif operation.entity_type == "guardian":
        phone = operation.payload.get("phone")
        if phone:
            existing = db.query(Guardian).filter(
                Guardian.school_id == operation.school_id,
                Guardian.phone == phone,
                Guardian.first_name == operation.payload.get("first_name", ""),
                Guardian.last_name == operation.payload.get("last_name", ""),
            ).first()
            if existing is not None:
                raise ValueError("Conflit de création: responsable déjà présent selon nom/prénom/téléphone")
    elif operation.entity_type == "student_guardian":
        payload = operation.payload
        student_ref = payload.get("student_entity_id") or payload.get("student_id")
        guardian_ref = payload.get("guardian_entity_id") or payload.get("guardian_id")
        if not student_ref or not guardian_ref:
            raise ValueError("student_entity_id et guardian_entity_id sont obligatoires")
        def _resolve(ref, entity_type):
            try:
                return int(ref)
            except (TypeError, ValueError):
                identity = db.query(SyncEntityIdentity).filter(
                    SyncEntityIdentity.school_id == operation.school_id,
                    SyncEntityIdentity.entity_type == entity_type,
                    SyncEntityIdentity.client_entity_id == str(ref),
                ).first()
                if identity is None:
                    raise ValueError(f"Identité client inconnue: {entity_type} {ref}")
                return identity.server_entity_id
        student_id = _resolve(student_ref, "student")
        guardian_id = _resolve(guardian_ref, "guardian")
        if db.query(Student).filter(Student.id == student_id, Student.school_id == operation.school_id).first() is None:
            raise ValueError("Élève introuvable dans cet établissement")
        if db.query(Guardian).filter(Guardian.id == guardian_id, Guardian.school_id == operation.school_id).first() is None:
            raise ValueError("Responsable introuvable dans cet établissement")
        if db.query(StudentGuardian).filter(StudentGuardian.student_id == student_id, StudentGuardian.guardian_id == guardian_id).first() is not None:
            raise ValueError("Ce responsable est déjà lié à cet élève")
    values = {k: _coerce_value(operation.entity_type, k, v) for k, v in operation.payload.items()}
    if operation.entity_type == "evaluation_result":
        student_ref = values.pop("student_entity_id", values.get("student_id"))
        values.pop("student_id", None)
        try:
            student_id = int(student_ref)
        except (TypeError, ValueError):
            identity = db.query(SyncEntityIdentity).filter(
                SyncEntityIdentity.school_id == operation.school_id,
                SyncEntityIdentity.entity_type == "student",
                SyncEntityIdentity.client_entity_id == str(student_ref),
            ).first()
            if identity is None:
                raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
            student_id = identity.server_entity_id
        values["student_id"] = student_id
        if values.get("max_score") is None:
            activity = db.query(EvaluationActivity).filter(EvaluationActivity.id == values["activity_id"]).first()
            values["max_score"] = activity.max_score if activity else None
        entity = EvaluationResult(**values)
        db.add(entity); db.flush()
        identity = SyncEntityIdentity(school_id=operation.school_id, device_id=operation.device_id, entity_type=operation.entity_type, client_entity_id=operation.entity_id, server_entity_id=entity.id)
        db.add(identity)
        return entity, identity
    if operation.entity_type == "grade":
        student_ref = values.pop("student_entity_id", values.get("student_id"))
        values.pop("student_id", None)
        try:
            student_id = int(student_ref)
        except (TypeError, ValueError):
            identity = db.query(SyncEntityIdentity).filter(
                SyncEntityIdentity.school_id == operation.school_id,
                SyncEntityIdentity.entity_type == "student",
                SyncEntityIdentity.client_entity_id == str(student_ref),
            ).first()
            if identity is None:
                raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
            student_id = identity.server_entity_id
        values["student_id"] = student_id
        entity = Grade(**values)
        db.add(entity)
        db.flush()
        identity = SyncEntityIdentity(
            school_id=operation.school_id, device_id=operation.device_id,
            entity_type=operation.entity_type, client_entity_id=operation.entity_id,
            server_entity_id=entity.id,
        )
        db.add(identity)
        return entity, identity
    if operation.entity_type == "student_guardian":
        student_ref = values.pop("student_entity_id", values.get("student_id"))
        guardian_ref = values.pop("guardian_entity_id", values.get("guardian_id"))
        values.pop("student_id", None)
        values.pop("guardian_id", None)
        def _resolve(ref, entity_type):
            try:
                return int(ref)
            except (TypeError, ValueError):
                identity = db.query(SyncEntityIdentity).filter(
                    SyncEntityIdentity.school_id == operation.school_id,
                    SyncEntityIdentity.entity_type == entity_type,
                    SyncEntityIdentity.client_entity_id == str(ref),
                ).first()
                if identity is None:
                    raise ValueError(f"Identité client inconnue: {entity_type} {ref}")
                return identity.server_entity_id
        values["student_id"] = _resolve(student_ref, "student")
        values["guardian_id"] = _resolve(guardian_ref, "guardian")
        entity = StudentGuardian(**values)
        db.add(entity)
        db.flush()
        identity = SyncEntityIdentity(school_id=operation.school_id, device_id=operation.device_id, entity_type=operation.entity_type, client_entity_id=operation.entity_id, server_entity_id=entity.id)
        db.add(identity)
        return entity, identity

    if operation.entity_type == "class_membership":
        student_ref = values.pop("student_entity_id", values.get("student_id"))
        values.pop("student_id", None)
        try:
            student_id = int(student_ref)
        except (TypeError, ValueError):
            identity = db.query(SyncEntityIdentity).filter(
                SyncEntityIdentity.school_id == operation.school_id,
                SyncEntityIdentity.entity_type == "student",
                SyncEntityIdentity.client_entity_id == str(student_ref),
            ).first()
            if identity is None:
                raise ValueError("Élève inconnu: synchroniser d'abord l'élève")
            student_id = identity.server_entity_id
        values["student_id"] = student_id
    entity = model(**values) if operation.entity_type == "class_membership" else model(school_id=operation.school_id, **values)
    db.add(entity)
    db.flush()
    identity = SyncEntityIdentity(
        school_id=operation.school_id, device_id=operation.device_id,
        entity_type=operation.entity_type, client_entity_id=operation.entity_id,
        server_entity_id=entity.id,
    )
    db.add(identity)
    return entity, identity


def apply_business_mutation(db, operation, expected_version: int) -> dict:
    """Applique une mutation métier contrôlée, y compris les créations offline."""
    if operation.entity_type not in ENTITY_HANDLERS:
        raise ValueError(f"Entité non synchronisable: {operation.entity_type}")
    if not isinstance(operation.payload, dict):
        raise ValueError("Payload de synchronisation invalide")
    if operation.operation_type != "delete" and not operation.payload:
        raise ValueError("Payload de synchronisation vide")
    allowed_fields = ALLOWED_FIELDS[operation.entity_type]
    if operation.operation_type == "transition" and operation.entity_type == "grade":
        allowed_fields = {"to_state"}
    unknown = set(operation.payload) - allowed_fields
    if unknown:
        raise ValueError(f"Champs non autorisés: {', '.join(sorted(unknown))}")
    if operation.operation_type == "update" and operation.entity_type == "evaluation_result" and "state" in operation.payload:
        raise ValueError("La modification d'état d'un résultat doit utiliser l'opération transition")
    if operation.operation_type == "update" and operation.entity_type == "grade" and "state" in operation.payload:
        raise ValueError("La modification d'état d'une note doit utiliser l'opération transition")

    if operation.operation_type == "create":
        if not operation.entity_id or len(str(operation.entity_id)) < 8:
            raise ValueError("entity_id client stable obligatoire pour une création offline")
        existing_identity = db.query(SyncEntityIdentity).filter(
            SyncEntityIdentity.school_id == operation.school_id,
            SyncEntityIdentity.entity_type == operation.entity_type,
            SyncEntityIdentity.client_entity_id == operation.entity_id,
        ).first()
        if existing_identity is not None:
            return {"entity_type": operation.entity_type, "entity_id": existing_identity.server_entity_id, "operation_type": "create", "idempotent_identity": True}
        entity, _identity = _create_business_entity(db, operation)
        return {"entity_type": operation.entity_type, "entity_id": entity.id, "operation_type": "create", "client_entity_id": operation.entity_id}

    if operation.operation_type == "transition":
        if operation.entity_type != "grade":
            raise ValueError("Les transitions synchronisées ne sont supportées que pour les notes")
        target_state = operation.payload.get("to_state")
        if not isinstance(target_state, str):
            raise ValueError("to_state est obligatoire pour une transition de note")
        if set(operation.payload) - {"to_state"}:
            raise ValueError("Une transition de note ne peut contenir que to_state")
        entity_id = _resolve_server_id(db, operation)
        if entity_id is None:
            raise ValueError("Identité client inconnue; synchronisation initiale requise")
        grade = db.query(Grade).filter(Grade.id == entity_id).first()
        if grade is None:
            raise ValueError("Note introuvable")
        assessment = _grade_period_is_closed(db, grade)
        school_class = db.query(SchoolClass).filter(SchoolClass.id == assessment.class_id, SchoolClass.school_id == operation.school_id).first()
        if school_class is None:
            raise ValueError("Note hors établissement")
        _validate_grade_transition(grade.state, target_state)
        history = GradeAudit(
            grade_id=grade.id, changed_by_id=operation.user_id,
            from_state=grade.state, to_state=target_state,
            old_score=grade.score, new_score=grade.score,
        )
        db.add(history)
        grade.state = target_state
        return {"entity_type": "grade", "entity_id": grade.id, "operation_type": "transition",
                "from_state": history.from_state, "to_state": target_state}

    model = ENTITY_HANDLERS[operation.entity_type]
    entity_id = _resolve_server_id(db, operation)
    if entity_id is None:
        raise ValueError("Identité client inconnue; synchronisation initiale requise")
    if operation.entity_type == "grade":
        entity = db.query(Grade).filter(Grade.id == entity_id).first()
        if entity is not None:
            assessment = db.query(Assessment).filter(Assessment.id == entity.assessment_id).first()
            if assessment is None or db.query(SchoolClass).filter(SchoolClass.id == assessment.class_id, SchoolClass.school_id == operation.school_id).first() is None:
                entity = None
    else:
        if operation.entity_type == "student_guardian":
            entity = db.query(model).join(Student, Student.id == model.student_id).filter(model.id == entity_id, Student.school_id == operation.school_id).first()
        else:
            entity = db.query(model).filter(model.id == entity_id, model.school_id == operation.school_id).first()
    if entity is None and operation.entity_type == "evaluation_result":
        entity = db.query(EvaluationResult).join(EvaluationActivity, EvaluationActivity.id == EvaluationResult.activity_id).join(SchoolClass, SchoolClass.id == EvaluationActivity.class_id).filter(EvaluationResult.id == entity_id, SchoolClass.school_id == operation.school_id).first()
    if entity is None:
        raise ValueError("Entité introuvable dans cet établissement")
    if operation.entity_type == "evaluation_result":
        _evaluation_result_context(db, entity)
    if operation.entity_type == "grade":
        _grade_period_is_closed(db, entity)
    if operation.operation_type == "delete":
        if operation.entity_type == "class_membership":
            entity.left_at = date.today()
        elif operation.entity_type == "grade":
            if entity.state in {"locked", "published"}:
                raise ValueError("Note verrouillée/publiée: suppression interdite")
            raise ValueError("Suppression de note interdite; utilisez une correction tracée")
        elif hasattr(entity, "is_active"):
            entity.is_active = False
        else:
            raise ValueError("Suppression non supportée pour cette entité")
    else:
        for field, raw_value in operation.payload.items():
            if operation.entity_type in {"class_membership", "grade", "evaluation_result"} and field in {"student_entity_id", "student_id"}:
                continue
            if operation.entity_type in {"grade", "evaluation_result"} and field in {"assessment_id", "activity_id", "state"}:
                continue
            if operation.entity_type == "grade" and entity.state in {"locked", "published"} and field in {"score", "is_absent", "comment"}:
                raise ValueError("Note verrouillée/publiée: modification interdite")
            if operation.entity_type == "evaluation_result" and entity.state in {"locked", "published"} and field in {"score", "max_score", "is_absent", "observation", "strengths", "needs_support"}:
                raise ValueError("Résultat verrouillé/publié: modification interdite")
            if operation.entity_type == "student" and field == "status" and raw_value == "active" and entity.status != "active":
                try:
                    enforce_subscription_capacity(db, operation.school_id, "students")
                except SubscriptionError as exc:
                    raise ValueError(str(exc)) from exc
            setattr(entity, field, _coerce_value(operation.entity_type, field, raw_value))
    return {"entity_type": operation.entity_type, "entity_id": entity.id, "operation_type": operation.operation_type}

