from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.services.operations_v4 import control_center, create_incident, resolve_incident, list_incidents, record_platform_snapshot

router=APIRouter(prefix='/api/operations',tags=['Control Center'])

class IncidentCreate(BaseModel):
    title: str=Field(min_length=3,max_length=180)
    category: str=Field(min_length=2,max_length=80)
    severity: str=Field(default='medium',pattern='^(low|medium|high|critical)$')
    description: str|None=None
    school_id: int|None=None
    metadata: dict={}

@router.get('/control-center',dependencies=[Depends(require_permission('administration.operations.view'))])
def control(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(status_code=403,detail='Accès réservé au contrôle central SIGMA')
    return control_center(db)

@router.get('/incidents',dependencies=[Depends(require_permission('administration.operations.view'))])
def incidents(school_id:int|None=None,status:str|None=None,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin and school_id not in (None,current_user.school_id): raise HTTPException(status_code=403,detail='Accès refusé')
    sid=None if current_user.is_superadmin else current_user.school_id
    return {'items':[{'id':x.id,'school_id':x.school_id,'severity':x.severity,'status':x.status,'category':x.category,'title':x.title,'description':x.description,'detected_at':x.detected_at.isoformat(),'resolved_at':x.resolved_at.isoformat() if x.resolved_at else None} for x in list_incidents(db,sid,status)]}

@router.post('/incidents',dependencies=[Depends(require_permission('administration.operations.execute'))])
def incident(payload:IncidentCreate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin and payload.school_id not in (None,current_user.school_id): raise HTTPException(status_code=403,detail='Accès refusé')
    x=create_incident(db,title=payload.title,category=payload.category,severity=payload.severity,description=payload.description,school_id=payload.school_id or current_user.school_id,actor=current_user,metadata=payload.metadata)
    return {'id':x.id,'status':x.status}

@router.post('/incidents/{incident_id}/resolve',dependencies=[Depends(require_permission('administration.operations.execute'))])
def resolve(incident_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    try: x=resolve_incident(db,incident_id,current_user)
    except PermissionError as exc: raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {'id':x.id,'status':x.status,'resolved_at':x.resolved_at.isoformat() if x.resolved_at else None}

@router.post('/snapshot',dependencies=[Depends(require_permission('administration.operations.execute'))])
def snapshot(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(status_code=403,detail='Accès réservé au contrôle central SIGMA')
    x=record_platform_snapshot(db)
    return {'id':x.id,'period_key':x.period_key,'schools':x.schools_count,'active_schools':x.active_schools,'users':x.users_count,'students':x.students_count,'open_incidents':x.open_incidents,'storage_bytes':x.storage_bytes}
