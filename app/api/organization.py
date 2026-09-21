from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.services.media import save_school_asset
from app.services.phone import normalize_international_phone
from app.services.matricule import validate_template, STRATEGIES

from app.core.database import get_db
from app.core.config import settings
from app.models.organization import Organization, School, Campus, AcademicYear, AcademicPeriod


def _assert_school_access(school_id: int, current_user: User) -> None:
    if not current_user.is_superadmin and current_user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Accès refusé à cet établissement")

router = APIRouter(prefix="/api", tags=["Établissement"])


class SchoolCreate(BaseModel):
    organization_id: int | None = None
    name: str
    short_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    phone_secondary: str | None = None
    ministry_name: str = "Ministère de l’Éducation de Base"
    school_type: str | None = None
    language: str = "fr"
    currency: str = "XAF"

    @field_validator("phone", "phone_secondary")
    @classmethod
    def _validate_phone(cls, v):
        return normalize_international_phone(v)


class SchoolSettingsUpdate(BaseModel):
    """Paramètres modifiables après création, réunis en un seul écran :
    coordonnées, format du matricule, canal de communication par défaut."""
    phone: str | None = None
    phone_secondary: str | None = None
    email: str | None = None
    matricule_strategy: str | None = None
    matricule_template: str | None = None
    communication_channel_default: str | None = None

    @field_validator("phone", "phone_secondary")
    @classmethod
    def _validate_phone(cls, v):
        return normalize_international_phone(v)

    @field_validator("communication_channel_default")
    @classmethod
    def _validate_channel(cls, v):
        if v is not None and v not in ("sms", "app", "both"):
            raise ValueError("communication_channel_default doit être 'sms', 'app' ou 'both'")
        return v


class AcademicYearCreate(BaseModel):
    school_id: int
    label: str
    start_date: str
    end_date: str
    is_current: bool = False


class AcademicPeriodCreate(BaseModel):
    academic_year_id: int
    name: str
    order_index: int = 1
    start_date: str
    end_date: str


@router.post("/organizations")
def create_organization(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Seul un superadministrateur peut créer un groupe")
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name}


@router.post("/schools", dependencies=[Depends(require_permission("administration.schools.create"))])
def create_school(payload: SchoolCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school = School(**payload.model_dump())
    db.add(school)
    db.commit()
    db.refresh(school)
    return {"id": school.id, "name": school.name}


@router.get("/schools/{school_id}")
def get_school(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")
    return {"id": school.id, "name": school.name, "short_name": school.short_name, "address": school.address, "phone": school.phone, "phone_secondary": school.phone_secondary, "email": school.email, "website": school.website, "logo_path": school.logo_path, "official_stamp_path": school.official_stamp_path, "ministry_name": school.ministry_name, "matricule_strategy": school.matricule_strategy, "matricule_template": school.matricule_template, "communication_channel_default": school.communication_channel_default}


@router.patch("/schools/{school_id}/settings", dependencies=[Depends(require_permission("administration.settings.modify"))])
def update_school_settings(school_id: int, payload: SchoolSettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Écran unique de paramétrage établissement : coordonnées, format du
    matricule et canal de communication par défaut (SMS/app mobile/les deux).
    """
    _assert_school_access(school_id, current_user)
    school = db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")

    data = payload.model_dump(exclude_unset=True)

    if "matricule_strategy" in data and data["matricule_strategy"] is not None:
        if data["matricule_strategy"] not in STRATEGIES:
            raise HTTPException(status_code=422, detail=f"Stratégie de matricule inconnue: {data['matricule_strategy']}")
    if "matricule_template" in data and data["matricule_template"] is not None:
        try:
            data["matricule_template"] = validate_template(data["matricule_template"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    for field, value in data.items():
        setattr(school, field, value)
    db.commit()
    db.refresh(school)
    return {"id": school.id, "phone": school.phone, "phone_secondary": school.phone_secondary, "email": school.email, "matricule_strategy": school.matricule_strategy, "matricule_template": school.matricule_template, "communication_channel_default": school.communication_channel_default}


@router.get("/schools/{school_id}/asset/{asset_type}")
def get_school_asset(school_id: int, asset_type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    school=db.get(School,school_id)
    if not school or asset_type not in ("logo","stamp"): raise HTTPException(status_code=404, detail="Ressource introuvable")
    rel=school.logo_path if asset_type=="logo" else school.official_stamp_path
    if not rel: raise HTTPException(status_code=404, detail="Ressource introuvable")
    path=__import__('app.services.media',fromlist=['resolve_media_path']).resolve_media_path(rel)
    if not path.exists(): raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/schools/{school_id}/logo", dependencies=[Depends(require_permission("administration.settings.modify"))])
def upload_school_logo(school_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    school = db.get(School, school_id)
    if not school: raise HTTPException(status_code=404, detail="Établissement introuvable")
    max_bytes = settings.MAX_SCHOOL_ASSET_BYTES
    raw = file.file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Logo trop volumineux")
    school.logo_path = save_school_asset(school_id, "logo", file, raw)
    db.commit(); return {"status":"ok", "logo_path":school.logo_path}


@router.post("/schools/{school_id}/stamp", dependencies=[Depends(require_permission("administration.settings.modify"))])
def upload_school_stamp(school_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    school = db.get(School, school_id)
    if not school: raise HTTPException(status_code=404, detail="Établissement introuvable")
    max_bytes = settings.MAX_SCHOOL_ASSET_BYTES
    raw = file.file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Cachet trop volumineux")
    school.official_stamp_path = save_school_asset(school_id, "stamp", file, raw)
    db.commit(); return {"status":"ok", "official_stamp_path":school.official_stamp_path}


@router.get("/schools")
def list_schools(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(School).filter(School.is_active.is_(True))
    if not current_user.is_superadmin:
        q = q.filter(School.id == current_user.school_id)
    schools = q.all()
    return [{"id": s.id, "name": s.name, "language": s.language, "currency": s.currency} for s in schools]


@router.post("/campuses", dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_campus(school_id: int, name: str, address: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    campus = Campus(school_id=school_id, name=name, address=address)
    db.add(campus)
    db.commit()
    db.refresh(campus)
    return {"id": campus.id, "name": campus.name}


@router.post("/academic-years", dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_academic_year(payload: AcademicYearCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(payload.school_id, current_user)
    from datetime import date as date_type

    if payload.is_current:
        db.query(AcademicYear).filter(AcademicYear.school_id == payload.school_id).update({"is_current": False})

    year = AcademicYear(
        school_id=payload.school_id,
        label=payload.label,
        start_date=date_type.fromisoformat(payload.start_date),
        end_date=date_type.fromisoformat(payload.end_date),
        is_current=payload.is_current,
    )
    db.add(year)
    db.commit()
    db.refresh(year)
    return {"id": year.id, "label": year.label}


@router.get("/academic-years")
def list_academic_years(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_school_access(school_id, current_user)
    years = db.query(AcademicYear).filter(AcademicYear.school_id == school_id).all()
    return [{"id": y.id, "label": y.label, "is_current": y.is_current, "is_archived": y.is_archived} for y in years]


@router.post("/academic-periods", dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_academic_period(payload: AcademicPeriodCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    year = db.get(AcademicYear, payload.academic_year_id)
    if not year:
        raise HTTPException(status_code=404, detail="Année scolaire introuvable")
    _assert_school_access(year.school_id, current_user)
    from datetime import date as date_type

    period = AcademicPeriod(
        academic_year_id=payload.academic_year_id,
        name=payload.name,
        order_index=payload.order_index,
        start_date=date_type.fromisoformat(payload.start_date),
        end_date=date_type.fromisoformat(payload.end_date),
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return {"id": period.id, "name": period.name}


@router.get("/academic-periods")
def list_academic_periods(academic_year_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    year = db.get(AcademicYear, academic_year_id)
    if not year:
        raise HTTPException(status_code=404, detail="Année scolaire introuvable")
    _assert_school_access(year.school_id, current_user)
    periods = db.query(AcademicPeriod).filter(AcademicPeriod.academic_year_id == academic_year_id).order_by(AcademicPeriod.order_index).all()
    return [{"id": p.id, "name": p.name, "is_grade_entry_open": p.is_grade_entry_open, "is_locked": p.is_locked} for p in periods]


