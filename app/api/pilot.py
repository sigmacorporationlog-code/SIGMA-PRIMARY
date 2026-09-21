from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.services.pilot import pilot_readiness, prepare_pilot

router = APIRouter(prefix="/api/pilot", tags=["Pilot école"])


def _access(school_id: int, user: User) -> None:
    if not user.is_superadmin and user.school_id != school_id:
        raise HTTPException(status_code=403, detail="Accès refusé à cet établissement")


class PilotPreparePayload(BaseModel):
    year_label: str = Field(min_length=4, max_length=20)
    start_date: date
    end_date: date
    period_count: int = Field(default=3, ge=1, le=6)


@router.get("/{school_id}/readiness", dependencies=[Depends(require_permission("administration.system.view"))])
def readiness(school_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    try:
        return pilot_readiness(db, school_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{school_id}/prepare", dependencies=[Depends(require_permission("administration.operations.execute"))])
def prepare(school_id: int, payload: PilotPreparePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _access(school_id, current_user)
    try:
        return prepare_pilot(db, school_id, current_user, payload.year_label, payload.start_date, payload.end_date, payload.period_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Préparation du pilote impossible: {exc}") from exc
