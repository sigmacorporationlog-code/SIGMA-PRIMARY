from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa
from app.core.database import Base
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.security import User, UserPost
from app.models.onboarding import SchoolOnboarding
from app.services.onboarding import bootstrap, get_or_create

def setup_db():
    e=create_engine('sqlite:///:memory:'); Base.metadata.create_all(e); db=sessionmaker(bind=e)()
    school=School(name='Onboarding School',currency='XAF',language='fr'); db.add(school); db.flush()
    actor=User(school_id=school.id,username='director',hashed_password='x',first_name='Dir',last_name='One'); db.add(actor); db.commit()
    return db,school,actor

def test_bootstrap_creates_current_year_periods_roles_subscription_and_actor_profile():
    db,school,actor=setup_db()
    state=bootstrap(db,school.id,actor,'2026/2027',date(2026,9,1),date(2027,6,30),3)
    assert state.status == 'completed'
    assert state.is_completed is True
    assert state.checklist['academic_year'] is True
    assert state.checklist['periods'] is True
    assert db.query(AcademicYear).filter_by(school_id=school.id,is_current=True).count()==1
    assert db.query(AcademicPeriod).count()==3
    assert db.query(UserPost).filter_by(user_id=actor.id).count() >= 1

def test_onboarding_state_is_created_without_marking_complete():
    db,school,actor=setup_db()
    state=get_or_create(db,school.id); db.commit()
    assert state.status == 'draft'
    assert state.is_completed is False
    assert db.query(SchoolOnboarding).filter_by(school_id=school.id).count()==1
