from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.organization import School
from app.services.onboarding import get_or_create, bootstrap

router = APIRouter(prefix='/api/onboarding', tags=['Onboarding'])

def access(school_id, user):
    if not user.is_superadmin and user.school_id != school_id:
        raise HTTPException(status_code=403, detail='Accès refusé à cet établissement')

class BootstrapPayload(BaseModel):
    year_label: str = Field(min_length=4, max_length=20)
    start_date: date
    end_date: date
    period_count: int = Field(default=3, ge=1, le=6)

@router.get('/{school_id}')
def state(school_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    access(school_id,current_user)
    if not db.get(School,school_id): raise HTTPException(404,'Établissement introuvable')
    s=get_or_create(db,school_id); db.commit(); db.refresh(s)
    return {'school_id':school_id,'status':s.status,'current_step':s.current_step,'checklist':s.checklist,'completed':s.is_completed}

@router.post('/{school_id}/bootstrap', dependencies=[Depends(require_permission("administration.settings.modify"))])
def run_bootstrap(school_id:int,payload:BootstrapPayload,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    access(school_id,current_user)
    if payload.end_date <= payload.start_date: raise HTTPException(400,'La date de fin doit être postérieure à la date de début')
    try: s=bootstrap(db,school_id,current_user,payload.year_label,payload.start_date,payload.end_date,payload.period_count)
    except ValueError as e: raise HTTPException(404,str(e))
    return {'school_id':school_id,'status':s.status,'checklist':s.checklist,'completed':s.is_completed}
