from datetime import datetime, timezone
from app.models.fleet_v4 import FleetInstallation
from app.models.organization import School
from app.services.fleet import heartbeat, fleet_overview, plan_rollout, evaluate_rollout

def _db():
    from tests.test_v438_sla import make_db
    return make_db()

def _school(db, name='École A'):
    s=School(name=name); db.add(s); db.commit(); db.refresh(s); return s

def test_heartbeat_and_overview_version_drift():
    db=_db(); s=_school(db)
    x=heartbeat(db,s.id,'instance-a','4.39.0',status='healthy',health='ready',backup_at=datetime.now(timezone.utc))
    assert x.school_id==s.id
    o=fleet_overview(db)
    assert o['counts']['installed']==1
    assert o['counts']['stale_versions']==1
    assert o['schools'][0]['installation']['instance_id']=='instance-a'

def test_rollout_pauses_when_failure_threshold_exceeded():
    db=_db(); s1=_school(db,'A'); s2=_school(db,'B')
    heartbeat(db,s1.id,'a','4.40.0',status='healthy')
    heartbeat(db,s2.id,'b','4.39.0',status='error')
    r=plan_rollout(db,'4.40.0',max_failure_percent=10)
    result=evaluate_rollout(db,r.id)
    assert result['status']=='paused'
    assert result['auto_abort'] is True

def test_active_rollout_is_singleton():
    db=_db(); plan_rollout(db,'4.40.0')
    try:
        plan_rollout(db,'4.40.1')
        assert False
    except ValueError as exc:
        assert 'déjà actif' in str(exc)
