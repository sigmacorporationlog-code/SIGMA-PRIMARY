from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.organization import School
from app.models.security import User
from app.models.students import Student
from app.models.cloud import SchoolSubscription
from app.models.operations_v4 import PlatformIncident, PlatformMetricSnapshot
from app.services.production import production_health, readiness, security_posture
from app.core.paths import data_dir
import shutil

SEVERITIES = {'low','medium','high','critical'}
STATUSES = {'open','acknowledged','resolved'}

def create_incident(db: Session, *, title: str, category: str, severity: str='medium', description: str|None=None, school_id: int|None=None, actor: User|None=None, metadata: dict|None=None):
    if severity not in SEVERITIES: raise ValueError('Gravité invalide')
    incident = PlatformIncident(school_id=school_id, severity=severity, status='open', category=category, title=title[:180], description=description, detected_at=datetime.now(timezone.utc), detected_by_user_id=actor.id if actor else None, metadata_json=metadata or {})
    db.add(incident); db.commit(); db.refresh(incident); return incident

def resolve_incident(db: Session, incident_id: int, actor: User|None=None):
    incident = db.get(PlatformIncident, incident_id)
    if not incident: raise ValueError('Incident introuvable')
    if actor is not None and not actor.is_superadmin and incident.school_id not in (None, actor.school_id):
        raise PermissionError('Accès refusé à cet établissement')
    if incident.status == 'resolved': return incident
    incident.status='resolved'; incident.resolved_at=datetime.now(timezone.utc); incident.resolved_by_user_id=actor.id if actor else None
    db.commit(); db.refresh(incident); return incident

def list_incidents(db: Session, school_id: int|None=None, status: str|None=None, limit: int=100):
    q=db.query(PlatformIncident).order_by(PlatformIncident.detected_at.desc())
    if school_id is not None: q=q.filter(PlatformIncident.school_id==school_id)
    if status: q=q.filter(PlatformIncident.status==status)
    return q.limit(min(max(limit,1),500)).all()

def record_platform_snapshot(db: Session, period_key: str|None=None):
    period_key = period_key or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H')
    schools=db.query(School).filter(School.is_active.is_(True)).count()
    active_subs=db.query(SchoolSubscription).filter(SchoolSubscription.status.in_(['trial','active'])).count()
    users=db.query(User).filter(User.is_active.is_(True)).count()
    students=db.query(Student).filter(Student.status=='active').count()
    incidents=db.query(PlatformIncident).filter(PlatformIncident.status!='resolved').count()
    usage=shutil.disk_usage(data_dir())
    snap=PlatformMetricSnapshot(period_key=period_key, schools_count=schools, active_schools=active_subs, users_count=users, students_count=students, open_incidents=incidents, storage_bytes=usage.used, metadata_json={'storage_free_bytes':usage.free})
    db.add(snap); db.commit(); db.refresh(snap); return snap

def control_center(db: Session) -> dict:
    health=production_health(db); ready=readiness(db); security=security_posture()
    schools=db.query(School).filter(School.is_active.is_(True)).order_by(School.name.asc()).all()
    open_count=db.query(PlatformIncident).filter(PlatformIncident.status!='resolved').count()
    critical=db.query(PlatformIncident).filter(PlatformIncident.status!='resolved', PlatformIncident.severity=='critical').count()
    return {'timestamp':datetime.now(timezone.utc).isoformat(),'health':health,'readiness':ready,'security':security,'schools':{'total':len(schools),'active_subscriptions':db.query(SchoolSubscription).filter(SchoolSubscription.status.in_(['trial','active'])).count()},'incidents':{'open':open_count,'critical':critical,'recent':[{'id':x.id,'school_id':x.school_id,'severity':x.severity,'status':x.status,'category':x.category,'title':x.title,'detected_at':x.detected_at.isoformat()} for x in list_incidents(db,status='open',limit=10)]}}
