from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.services.fleet import heartbeat, fleet_overview, plan_rollout, evaluate_rollout

router=APIRouter(prefix='/api/system/fleet', tags=['Fleet Management'])

class HeartbeatIn(BaseModel):
    school_id:int
    instance_id:str=Field(min_length=3,max_length=120)
    version:str=Field(min_length=1,max_length=40)
    status:str=Field(default='healthy',pattern='^(healthy|unhealthy|offline|error)$')
    health:str=Field(default='ready',pattern='^(ready|not_ready|unknown)$')
    backup_at:datetime|None=None
    sync_at:datetime|None=None
    disk_free_bytes:int|None=Field(default=None,ge=0)
    metadata:dict={}

class RolloutIn(BaseModel):
    target_version:str=Field(min_length=1,max_length=40)
    channel:str=Field(default='commercial',max_length=30)
    strategy:str=Field(default='canary',pattern='^(canary|progressive|all)$')
    canary_percent:int=Field(default=10,ge=1,le=100)
    max_failure_percent:int=Field(default=10,ge=0,le=100)

@router.get('/overview', dependencies=[Depends(require_permission('administration.operations.view'))])
def overview(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(status_code=403,detail='Accès réservé au contrôle central SIGMA')
    return fleet_overview(db)

@router.post('/heartbeat', dependencies=[Depends(require_permission('administration.operations.execute'))])
def fleet_heartbeat(payload:HeartbeatIn, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin and payload.school_id != current_user.school_id: raise HTTPException(status_code=403,detail='Accès refusé')
    x=heartbeat(db, payload.school_id, payload.instance_id, payload.version, status=payload.status, health=payload.health, backup_at=payload.backup_at, sync_at=payload.sync_at, disk_free_bytes=payload.disk_free_bytes, metadata=payload.metadata)
    return {'id':x.id,'school_id':x.school_id,'instance_id':x.instance_id,'version':x.installed_version,'status':x.status,'last_seen_at':x.last_seen_at.isoformat()}

@router.post('/rollouts', dependencies=[Depends(require_permission('administration.operations.execute'))])
def rollout(payload:RolloutIn, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(status_code=403,detail='Accès réservé au contrôle central SIGMA')
    try: x=plan_rollout(db,**payload.model_dump())
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
    return {'id':x.id,'status':x.status,'target_version':x.target_version,'strategy':x.strategy,'canary_percent':x.canary_percent,'max_failure_percent':x.max_failure_percent}

@router.post('/rollouts/{rollout_id}/evaluate', dependencies=[Depends(require_permission('administration.operations.execute'))])
def rollout_evaluate(rollout_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(status_code=403,detail='Accès réservé au contrôle central SIGMA')
    try: return evaluate_rollout(db,rollout_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
