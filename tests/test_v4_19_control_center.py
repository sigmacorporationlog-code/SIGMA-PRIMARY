from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.core.database import Base
from app.models.organization import School
from app.models.security import User
from app.services.operations_v4 import create_incident, resolve_incident, record_platform_snapshot, control_center

def setup_db():
    e=create_engine('sqlite:///:memory:'); Base.metadata.create_all(e); db=sessionmaker(bind=e)()
    school=School(name='Control School',currency='XAF',language='fr'); db.add(school); db.flush()
    user=User(school_id=school.id,username='admin',hashed_password='x',first_name='Admin',last_name='One',is_superadmin=True); db.add(user); db.commit()
    return db,school,user

def test_incident_lifecycle():
    db,school,user=setup_db()
    x=create_incident(db,title='Base indisponible',category='database',severity='critical',school_id=school.id,actor=user)
    assert x.status=='open'
    x=resolve_incident(db,x.id,user)
    assert x.status=='resolved' and x.resolved_at is not None

def test_snapshot_and_control_center():
    db,school,user=setup_db()
    create_incident(db,title='Test',category='operations',school_id=school.id,actor=user)
    snap=record_platform_snapshot(db,'2026-09-15T10')
    assert snap.schools_count==1 and snap.open_incidents==1
    state=control_center(db)
    assert state['schools']['total']==1
    assert state['incidents']['open']==1
    assert state['incidents']['critical']==0
