"""SIGMA V4.40 fleet inventory, rollout planning and health aggregation."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.cloud import CloudEvent, SchoolSubscription
from app.models.fleet_v4 import FleetInstallation, FleetRollout
from app.models.organization import School
from app.models.security import User
from app.models.students import Student
from app.models.operations_v4 import PlatformIncident


def _now(): return datetime.now(timezone.utc)

def heartbeat(db: Session, school_id: int, instance_id: str, version: str, *, status="healthy", health="ready", backup_at=None, sync_at=None, disk_free_bytes=None, metadata=None):
    if not instance_id or len(instance_id) > 120: raise ValueError("instance_id invalide")
    row = db.query(FleetInstallation).filter(FleetInstallation.school_id == school_id).first()
    if not row:
        row = FleetInstallation(school_id=school_id, instance_id=instance_id[:120], installed_version=version[:40])
        db.add(row)
    row.instance_id = instance_id[:120]; row.installed_version = version[:40]; row.status = status[:30]; row.last_health = health[:30]; row.last_seen_at = _now()
    if backup_at: row.last_backup_at = backup_at
    if sync_at: row.last_sync_at = sync_at
    if disk_free_bytes is not None: row.disk_free_bytes = max(0, int(disk_free_bytes))
    row.metadata_json = metadata or row.metadata_json or {}
    db.commit(); db.refresh(row)
    return row


def fleet_overview(db: Session) -> dict:
    schools = db.query(School).filter(School.is_active.is_(True)).order_by(School.name.asc()).all()
    installations = {x.school_id: x for x in db.query(FleetInstallation).all()}
    items=[]
    for school in schools:
        inst=installations.get(school.id); sub=db.query(SchoolSubscription).filter(SchoolSubscription.school_id==school.id).first()
        users=db.query(User).filter(User.school_id==school.id, User.is_active.is_(True)).count()
        students=db.query(Student).filter(Student.school_id==school.id, Student.status=='active').count()
        incidents=db.query(PlatformIncident).filter(PlatformIncident.school_id==school.id, PlatformIncident.status!='resolved').count()
        items.append({'school':{'id':school.id,'name':school.name,'organization_id':school.organization_id},'installation':None if not inst else {'id':inst.id,'instance_id':inst.instance_id,'version':inst.installed_version,'channel':inst.channel,'status':inst.status,'last_seen_at':inst.last_seen_at.isoformat() if inst.last_seen_at else None,'last_backup_at':inst.last_backup_at.isoformat() if inst.last_backup_at else None,'last_sync_at':inst.last_sync_at.isoformat() if inst.last_sync_at else None,'health':inst.last_health,'disk_free_bytes':inst.disk_free_bytes},'subscription':None if not sub else {'plan':sub.plan_code,'status':sub.status,'ends_on':sub.ends_on.isoformat() if sub.ends_on else None},'usage':{'users':users,'students':students},'open_incidents':incidents})
    current=settings.V3_VERSION.split('-')[0]
    versions=[x['installation']['version'] for x in items if x['installation']]
    stale=[x for x in items if x['installation'] and x['installation']['version'] != current]
    return {'current_version':current,'counts':{'schools':len(items),'installed':len(versions),'healthy':sum(x['installation'] and x['installation']['status']=='healthy' for x in items),'stale_versions':len(stale),'open_incidents':sum(x['open_incidents'] for x in items)},'schools':items}


def plan_rollout(db: Session, target_version: str, *, channel='commercial', strategy='canary', canary_percent=10, max_failure_percent=10):
    if not target_version or len(target_version)>40: raise ValueError('Version cible invalide')
    if strategy not in {'canary','progressive','all'}: raise ValueError('Stratégie invalide')
    if not 1 <= canary_percent <= 100 or not 0 <= max_failure_percent <= 100: raise ValueError('Seuil de rollout invalide')
    active=db.query(FleetRollout).filter(FleetRollout.status.in_(['planned','running','paused'])).first()
    if active: raise ValueError('Un rollout est déjà actif')
    row=FleetRollout(target_version=target_version,channel=channel,strategy=strategy,status='planned',canary_percent=canary_percent,max_failure_percent=max_failure_percent,metadata_json={'created_by':'control_plane','auto_abort_on_failure':True})
    db.add(row); db.commit(); db.refresh(row); return row


def evaluate_rollout(db: Session, rollout_id: int):
    row=db.get(FleetRollout, rollout_id)
    if not row: raise ValueError('Rollout introuvable')
    installations=db.query(FleetInstallation).all()
    targeted=[x for x in installations if x.channel==row.channel]
    failures=[x for x in targeted if x.status in {'error','offline','unhealthy'}]
    failure_pct=(len(failures)*100/len(targeted)) if targeted else 0.0
    if failure_pct > row.max_failure_percent:
        row.status='paused'; row.metadata_json={**(row.metadata_json or {}),'abort_reason':'failure_threshold','failure_percent':round(failure_pct,2)}
    elif targeted and all(x.installed_version==row.target_version and x.status=='healthy' for x in targeted):
        row.status='completed'; row.completed_at=_now()
    db.commit(); db.refresh(row)
    return {'rollout_id':row.id,'status':row.status,'targeted':len(targeted),'failures':len(failures),'failure_percent':round(failure_pct,2),'auto_abort':row.status=='paused'}
