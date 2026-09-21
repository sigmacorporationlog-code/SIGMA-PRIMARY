from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cloud import CloudEvent, SchoolSubscription
from app.models.organization import School
from app.models.security import AuditLog, User
from app.models.students import Student


def ensure_subscription(db: Session, school_id: int, commit: bool = True) -> SchoolSubscription:
    sub = db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school_id).first()
    if sub:
        return sub
    sub = SchoolSubscription(
        school_id=school_id,
        plan_code="standard",
        status="trial",
        starts_on=date.today(),
        ends_on=date.today() + timedelta(days=TRIAL_DURATION_DAYS),
        max_users=50,
        max_students=1000,
        features={"cloud_sync": True, "offline": True, "insight": True, "connect": True},
    )
    db.add(sub)
    if commit:
        db.commit()
        db.refresh(sub)
    return sub


class SubscriptionError(Exception):
    """Base exception for commercial subscription enforcement."""


class SubscriptionInactiveError(SubscriptionError):
    """L'abonnement est expiré, suspendu ou inexistant."""


class SubscriptionCapacityError(SubscriptionError):
    """La capacité contractuelle du plan est atteinte."""


class SubscriptionFeatureError(SubscriptionError):
    """La fonctionnalité demandée n'est pas comprise dans le plan."""


def enforce_subscription_active(db: Session, school_id: int) -> SchoolSubscription:
    """Require a non-expired trial/active subscription for a protected action."""
    sub = ensure_subscription(db, school_id)
    state = subscription_state(db, school_id)
    if not state["active"]:
        raise SubscriptionInactiveError(f"Abonnement {state['status']} pour l'établissement {school_id}")
    return sub


def _validate_plan_bounds(sub: SchoolSubscription, plan: CloudPlan) -> None:
    """Ensure a subscription cannot exceed the commercial catalogue contract."""
    if sub.max_users > plan.max_users:
        raise SubscriptionCapacityError(
            f"Limite utilisateurs ({sub.max_users}) supérieure au plafond du plan {plan.code} ({plan.max_users})"
        )
    if sub.max_students > plan.max_students:
        raise SubscriptionCapacityError(
            f"Limite élèves ({sub.max_students}) supérieure au plafond du plan {plan.code} ({plan.max_students})"
        )
    requested = sub.features or {}
    allowed = plan.features or {}
    forbidden = sorted(k for k, enabled in requested.items() if bool(enabled) and not bool(allowed.get(k, False)))
    if forbidden:
        raise SubscriptionFeatureError(
            f"Fonctionnalités non incluses dans le plan {plan.code}: {', '.join(forbidden)}"
        )


def enforce_subscription_capacity(db: Session, school_id: int, resource: str) -> dict:
    """Enforce plan capacity before creating a user or active student."""
    sub = enforce_subscription_active(db, school_id)
    if resource == "users":
        current = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
        limit = sub.max_users
    elif resource == "students":
        current = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
        limit = sub.max_students
    else:
        raise ValueError("Ressource d'abonnement inconnue")
    if current >= limit:
        raise SubscriptionCapacityError(f"Limite {resource} atteinte ({limit}) pour le plan {sub.plan_code}")
    return {"resource": resource, "current": current, "limit": limit, "plan": sub.plan_code}


def validate_subscription_usage(db: Session, school_id: int, require_active: bool = True) -> dict:
    """Validate that current usage does not exceed the commercial contract.

    This is intentionally stricter than ``enforce_subscription_capacity``: it
    is used after bulk/restore/sync boundaries where an entire data set may be
    introduced at once.
    """
    sub = ensure_subscription(db, school_id)
    if require_active:
        state = subscription_state(db, school_id)
        if not state["active"]:
            raise SubscriptionInactiveError(f"Abonnement {state['status']} pour l'établissement {school_id}")
    users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
    students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    if users > sub.max_users:
        raise SubscriptionCapacityError(
            f"Données restaurées/synchronisées incompatibles: {users} utilisateurs actifs pour une limite de {sub.max_users}"
        )
    if students > sub.max_students:
        raise SubscriptionCapacityError(
            f"Données restaurées/synchronisées incompatibles: {students} élèves actifs pour une limite de {sub.max_students}"
        )
    return {"school_id": school_id, "users": users, "students": students, "max_users": sub.max_users, "max_students": sub.max_students}


def enforce_subscription_feature(db: Session, school_id: int, feature: str) -> SchoolSubscription:
    """Require an enabled commercial feature for a school."""
    sub = enforce_subscription_active(db, school_id)
    if not bool((sub.features or {}).get(feature, False)):
        raise SubscriptionFeatureError(f"Fonctionnalité non incluse dans le plan: {feature}")
    return sub


def subscription_state(db: Session, school_id: int) -> dict:
    sub = ensure_subscription(db, school_id)
    today = date.today()
    status = sub.status
    if status == "active" and sub.ends_on and sub.ends_on < today:
        status = "expired"
    active = status in {"trial", "active"} and (sub.ends_on is None or sub.ends_on >= today)
    users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
    students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    return {
        "school_id": school_id,
        "subscription_id": sub.id,
        "plan": sub.plan_code,
        "status": status,
        "active": active,
        "starts_on": sub.starts_on.isoformat(),
        "ends_on": sub.ends_on.isoformat() if sub.ends_on else None,
        "days_remaining": (sub.ends_on - today).days if sub.ends_on else None,
        "usage": {"users": users, "students": students},
        "limits": {"users": sub.max_users, "students": sub.max_students},
        "features": sub.features or {},
        "last_checked_at": sub.last_checked_at.isoformat() if sub.last_checked_at else None,
    }


def log_cloud_event(db: Session, school_id: int, event_type: str, actor: User | None, details: dict | None = None, success: bool = True) -> CloudEvent:
    event = CloudEvent(
        school_id=school_id,
        event_type=event_type,
        at=datetime.now(timezone.utc),
        actor_user_id=actor.id if actor else None,
        details=details or {},
        success=success,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _canonical_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat()


def audit_chain_digest(entry: AuditLog, previous_hash: str) -> str:
    payload = {
        "id": entry.id,
        "school_id": entry.school_id,
        "user_id": entry.user_id,
        "at": _canonical_datetime(entry.at),
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "old_value": entry.old_value,
        "new_value": entry.new_value,
        "ip_address": entry.ip_address,
        "device": entry.device,
        "previous_hash": previous_hash,
    }
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def verify_audit_chain(db: Session, school_id: int | None = None, limit: int = 10000) -> dict:
    query = db.query(AuditLog).order_by(AuditLog.id.asc())
    if school_id is not None:
        query = query.filter(AuditLog.school_id == school_id)
    rows = query.limit(limit).all()
    previous = "GENESIS"
    checked = 0
    legacy = 0
    broken = None
    for row in rows:
        if not row.entry_hash:
            legacy += 1
            previous = "LEGACY:" + str(row.id)
            continue
        if row.previous_hash != previous:
            broken = {"id": row.id, "reason": "previous_hash_mismatch"}
            break
        expected = audit_chain_digest(row, previous)
        if row.entry_hash != expected:
            broken = {"id": row.id, "reason": "entry_hash_mismatch"}
            break
        previous = row.entry_hash
        checked += 1
    return {"valid": broken is None, "checked": checked, "legacy_entries": legacy, "broken_at": broken}

# --- SIGMA V4 Control Plane -------------------------------------------------
from calendar import monthrange
from datetime import timedelta
from secrets import token_urlsafe
from pathlib import Path as _Path
from app.models.cloud import CloudPlan, CloudUsageSnapshot
from app.models.sync import SyncOperation
from app.core.paths import data_dir as _data_dir

TRIAL_DURATION_DAYS = 30

DEFAULT_CLOUD_PLANS = (
    {
        "code": "starter", "name": "SIGMA Starter", "monthly_price_xaf": 15000, "annual_price_xaf": 150000,
        "max_users": 15, "max_students": 500,
        "features": {"cloud_sync": True, "offline": True, "insight": False, "connect": True, "whatsapp": False, "mobile_money": False},
        "sort_order": 10,
    },
    {
        "code": "standard", "name": "SIGMA Standard", "monthly_price_xaf": 30000, "annual_price_xaf": 300000,
        "max_users": 50, "max_students": 1500,
        "features": {"cloud_sync": True, "offline": True, "insight": True, "connect": True, "whatsapp": True, "mobile_money": True},
        "sort_order": 20,
    },
    {
        "code": "premium", "name": "SIGMA Premium", "monthly_price_xaf": 60000, "annual_price_xaf": 600000,
        "max_users": 150, "max_students": 5000,
        "features": {"cloud_sync": True, "offline": True, "insight": True, "connect": True, "whatsapp": True, "mobile_money": True, "multi_campus": True, "priority_support": True},
        "sort_order": 30,
    },
)


def ensure_default_plans(db: Session) -> list[CloudPlan]:
    plans = []
    for payload in DEFAULT_CLOUD_PLANS:
        plan = db.query(CloudPlan).filter(CloudPlan.code == payload["code"]).first()
        if not plan:
            plan = CloudPlan(**payload)
            db.add(plan)
        plans.append(plan)
    db.commit()
    for plan in plans:
        db.refresh(plan)
    return plans


def get_plan(db: Session, code: str) -> CloudPlan | None:
    return db.query(CloudPlan).filter(CloudPlan.code == code, CloudPlan.is_active.is_(True)).first()


def issue_license_key(db: Session, school_id: int, plan_code: str, days: int, actor: User | None = None) -> dict:
    if days < 1 or days > 3650:
        raise ValueError("Durée de licence invalide")
    plan = get_plan(db, plan_code)
    if not plan:
        # Populate only missing catalogue defaults, but never resurrect or use
        # an explicitly deactivated commercial plan for a new licence.
        ensure_default_plans(db)
        plan = get_plan(db, plan_code)
    if not plan:
        raise ValueError("Plan Cloud inconnu ou inactif")
    raw = f"SIGMA-{plan.code.upper()}-{token_urlsafe(18).replace('-', '').replace('_', '')[:24].upper()}"
    digest = sha256(raw.encode("utf-8")).hexdigest()
    sub = ensure_subscription(db, school_id, commit=False)
    # Never issue a smaller licence over a currently-used subscription.
    current_users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
    current_students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    if current_users > plan.max_users or current_students > plan.max_students:
        raise SubscriptionCapacityError(
            f"Le plan {plan.code} est incompatible avec l'usage actuel: {current_users} utilisateurs actifs, {current_students} élèves actifs"
        )
    sub.plan_code = plan.code
    sub.status = "active"
    sub.starts_on = date.today()
    sub.ends_on = date.today() + timedelta(days=days)
    sub.max_users = plan.max_users
    sub.max_students = plan.max_students
    sub.features = dict(plan.features or {})
    sub.license_key_hash = digest
    sub.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    log_cloud_event(db, school_id, "license.issued", actor, {"plan": plan.code, "days": days})
    return {"license_key": raw, "school_id": school_id, "plan": plan.code, "ends_on": sub.ends_on.isoformat()}


def activate_license(db: Session, school_id: int, license_key: str, actor: User | None = None) -> dict:
    if not license_key or len(license_key) > 200:
        raise ValueError("Clé de licence invalide")
    sub = ensure_subscription(db, school_id, commit=False)
    if not sub.license_key_hash or sha256(license_key.strip().encode("utf-8")).hexdigest() != sub.license_key_hash:
        log_cloud_event(db, school_id, "license.activation_failed", actor, {}, success=False)
        raise ValueError("Clé de licence invalide")
    if not sub.ends_on or sub.ends_on < date.today():
        log_cloud_event(db, school_id, "license.activation_failed", actor, {"reason": "license_expired"}, success=False)
        raise ValueError("Licence expirée")
    sub.status = "active"
    sub.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    log_cloud_event(db, school_id, "license.activated", actor, {})
    return subscription_state(db, school_id)


def control_plane_overview(db: Session) -> dict:
    schools = db.query(School).filter(School.is_active.is_(True)).order_by(School.name.asc()).all()
    items = []
    for school in schools:
        state = subscription_state(db, school.id)
        items.append({"school": {"id": school.id, "name": school.name, "organization_id": school.organization_id}, "subscription": state})
    counts = {"total": len(items), "active": sum(1 for x in items if x["subscription"]["active"]), "expired": sum(1 for x in items if x["subscription"]["status"] == "expired"), "suspended": sum(1 for x in items if x["subscription"]["status"] == "suspended")}
    return {"counts": counts, "schools": items}


def record_usage_snapshot(db: Session, school_id: int, period_key: str | None = None) -> CloudUsageSnapshot:
    period_key = period_key or date.today().strftime("%Y-%m")
    users = db.query(User).filter(User.school_id == school_id, User.is_active.is_(True)).count()
    students = db.query(Student).filter(Student.school_id == school_id, Student.status == "active").count()
    sync_ops = db.query(SyncOperation).filter(SyncOperation.school_id == school_id).count() if hasattr(SyncOperation, "school_id") else 0
    storage = 0
    try:
        root = _data_dir() / "media" / str(school_id)
        if root.exists():
            storage = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    except OSError:
        storage = 0
    snap = db.query(CloudUsageSnapshot).filter(CloudUsageSnapshot.school_id == school_id, CloudUsageSnapshot.period_key == period_key).first()
    payload = {"users_count": users, "students_count": students, "storage_bytes": storage, "sync_operations": sync_ops, "api_requests": 0, "metadata_json": {"captured_at": datetime.now(timezone.utc).isoformat()}}
    if snap:
        for k, v in payload.items(): setattr(snap, k, v)
    else:
        snap = CloudUsageSnapshot(school_id=school_id, period_key=period_key, **payload)
        db.add(snap)
    db.commit(); db.refresh(snap)
    return snap


def governance_control_plane(db: Session) -> dict:
    """Return a central, read-only governance snapshot for superadmins."""
    from app.models.organization import School
    schools = db.query(School).filter(School.is_active.is_(True)).order_by(School.name.asc()).all()
    items = []
    for school in schools:
        state = subscription_state(db, school.id)
        events = db.query(CloudEvent).filter(CloudEvent.school_id == school.id).count()
        items.append({
            "school": {"id": school.id, "name": school.name, "organization_id": school.organization_id},
            "subscription": state,
            "cloud_events": events,
            "audit_integrity": verify_audit_chain(db, school.id, limit=10000),
        })
    return {
        "counts": {
            "schools": len(items),
            "active_subscriptions": sum(1 for x in items if x["subscription"]["active"]),
            "expired_subscriptions": sum(1 for x in items if x["subscription"]["status"] == "expired"),
            "suspended_subscriptions": sum(1 for x in items if x["subscription"]["status"] == "suspended"),
        },
        "schools": items,
    }
