from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.cloud import SchoolSubscription
from app.models.organization import School
from app.models.security import User
from app.services.cloud import (ensure_subscription, log_cloud_event, subscription_state, verify_audit_chain,
    ensure_default_plans, get_plan, issue_license_key, activate_license, control_plane_overview, record_usage_snapshot, governance_control_plane,
    validate_subscription_usage, SubscriptionCapacityError, SubscriptionFeatureError)

router = APIRouter(prefix="/api/cloud", tags=["SIGMA Cloud"])


def _access(school_id: int, user: User):
    if user.is_superadmin or user.school_id == school_id:
        return
    raise HTTPException(status_code=403, detail="Accès refusé à cet établissement")


class SubscriptionUpdate(BaseModel):
    plan_code: str = Field(min_length=2, max_length=50)
    status: str = Field(pattern="^(trial|active|suspended|expired)$")
    starts_on: date
    ends_on: date | None = None
    max_users: int = Field(ge=1, le=100000)
    max_students: int = Field(ge=1, le=10000000)
    features: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_lifecycle(self):
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on doit être postérieure ou égale à starts_on")
        if self.status in {"trial", "active"} and self.ends_on is None:
            raise ValueError("Une licence trial/active doit avoir une date de fin")
        if self.status == "active" and self.starts_on > date.today():
            raise ValueError("Une licence active ne peut pas commencer dans le futur")
        return self
    notes: str | None = None


@router.get("/overview")
def cloud_overview(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    state = subscription_state(db, school_id)
    return {"school": {"id": school.id, "name": school.name, "organization_id": school.organization_id}, "subscription": state, "audit_integrity": verify_audit_chain(db, school_id, limit=10000)}


@router.get("/subscription")
def cloud_subscription(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    return subscription_state(db, school_id)


@router.put("/subscription")
def update_subscription(school_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Seul un superadministrateur peut modifier une licence Cloud")
    if not db.get(School, school_id):
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    plan = get_plan(db, payload.plan_code)
    if not plan:
        raise HTTPException(status_code=400, detail="Plan Cloud inconnu ou inactif")
    # Superadmin may administer lifecycle dates/status, but cannot silently
    # grant capacity/features beyond the published commercial plan.
    if payload.max_users > plan.max_users:
        raise HTTPException(status_code=400, detail=f"max_users dépasse le plafond du plan {plan.code}")
    if payload.max_students > plan.max_students:
        raise HTTPException(status_code=400, detail=f"max_students dépasse le plafond du plan {plan.code}")
    requested_features = payload.features or {}
    forbidden = sorted(k for k, enabled in requested_features.items() if bool(enabled) and not bool((plan.features or {}).get(k, False)))
    if forbidden:
        raise HTTPException(status_code=400, detail=f"Fonctionnalités non incluses dans le plan {plan.code}: {', '.join(forbidden)}")
    sub = ensure_subscription(db, school_id, commit=False)
    previous = {"plan": sub.plan_code, "status": sub.status, "max_users": sub.max_users, "max_students": sub.max_students, "features": sub.features or {}}
    for key, value in payload.model_dump().items():
        setattr(sub, key, value)
    try:
        validate_subscription_usage(db, school_id, require_active=False)
    except (SubscriptionCapacityError, SubscriptionFeatureError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    log_cloud_event(db, school_id, "subscription.updated", current_user, {"before": previous, "after": {"plan": sub.plan_code, "status": sub.status, "max_users": sub.max_users, "max_students": sub.max_students, "features": sub.features or {}}})
    return subscription_state(db, school_id)


@router.post("/subscription/check")
def check_subscription(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    sub = ensure_subscription(db, school_id, commit=False)
    from datetime import datetime, timezone
    sub.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    return subscription_state(db, school_id)


@router.get("/audit/integrity")
def audit_integrity(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    return verify_audit_chain(db, school_id, limit=10000)


class LicenseIssue(BaseModel):
    school_id: int = Field(ge=1)
    plan_code: str = Field(min_length=2, max_length=50)
    days: int = Field(ge=1, le=3650)


class LicenseActivation(BaseModel):
    school_id: int = Field(ge=1)
    license_key: str = Field(min_length=10, max_length=200)


@router.get("/plans")
def cloud_plans(db: Session = Depends(get_db)):
    return {"items": [
        {"code": p.code, "name": p.name, "description": p.description, "monthly_price_xaf": p.monthly_price_xaf,
         "annual_price_xaf": p.annual_price_xaf, "max_users": p.max_users, "max_students": p.max_students,
         "features": p.features or {}, "sort_order": p.sort_order}
        for p in sorted(ensure_default_plans(db), key=lambda x: x.sort_order)
    ]}


@router.get("/control-plane")
def control_plane(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Accès réservé au contrôle central SIGMA")
    return control_plane_overview(db)


@router.post("/license/issue")
def license_issue(payload: LicenseIssue, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Seul un superadministrateur peut émettre une licence")
    if not db.get(School, payload.school_id):
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    try:
        return issue_license_key(db, payload.school_id, payload.plan_code, payload.days, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/license/activate")
def license_activate(payload: LicenseActivation, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(payload.school_id, current_user)
    try:
        return activate_license(db, payload.school_id, payload.license_key, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/usage/snapshot")
def usage_snapshot(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    snap = record_usage_snapshot(db, school_id)
    return {"id": snap.id, "school_id": snap.school_id, "period_key": snap.period_key, "users": snap.users_count,
            "students": snap.students_count, "storage_bytes": snap.storage_bytes, "api_requests": snap.api_requests,
            "sync_operations": snap.sync_operations, "created_at": snap.created_at.isoformat() if snap.created_at else None}


@router.get('/governance')
def governance(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail='Accès réservé au contrôle central SIGMA')
    return governance_control_plane(db)
