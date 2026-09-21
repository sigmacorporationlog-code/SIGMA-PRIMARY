from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa
from app.core.database import Base
from app.models.organization import School, AcademicYear
from app.models.security import User
from app.models.students import Level, Stream, SchoolClass, ClassMembership, Student
from app.api.students import update_level, deactivate_level, update_class, deactivate_class
from app.schemas.students import LevelUpdate, SchoolClassUpdate


def db_setup():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e, sessionmaker(bind=e)()


def actor(school_id):
    return User(school_id=school_id, username=f"admin{school_id}", hashed_password="x", first_name="Admin", last_name="Test")


def test_level_can_be_corrected_and_deactivated_without_hard_delete():
    e, db = db_setup()
    school = School(name="Pilot", currency="XAF", language="fr"); db.add(school); db.flush()
    user = actor(school.id); db.add(user); level = Level(school_id=school.id, name="CE1", order_index=2); db.add(level); db.commit()
    updated = update_level(level.id, LevelUpdate(name="CE2", order_index=3), db, user)
    assert updated["name"] == "CE2" and updated["order_index"] == 3
    result = deactivate_level(level.id, db, user)
    assert result["is_active"] is False
    assert db.get(Level, level.id) is not None
    e.dispose()


def test_level_cannot_be_deactivated_while_used_by_active_class():
    e, db = db_setup()
    school = School(name="Pilot", currency="XAF", language="fr"); db.add(school); db.flush()
    user = actor(school.id); year=AcademicYear(school_id=school.id,label="2026/2027",start_date=date(2026,9,1),end_date=date(2027,7,31),is_current=True)
    level=Level(school_id=school.id,name="CE1",order_index=1); db.add_all([user,year,level]); db.flush()
    cls=SchoolClass(school_id=school.id,academic_year_id=year.id,level_id=level.id,name="CE1 A"); db.add(cls); db.commit()
    with pytest.raises(HTTPException) as exc: deactivate_level(level.id, db, user)
    assert exc.value.status_code == 409
    e.dispose()


def test_class_can_be_corrected_and_deactivated_when_empty():
    e, db = db_setup()
    school=School(name="Pilot",currency="XAF",language="fr"); db.add(school); db.flush()
    user=actor(school.id); year=AcademicYear(school_id=school.id,label="2026/2027",start_date=date(2026,9,1),end_date=date(2027,7,31),is_current=True); level=Level(school_id=school.id,name="CE1",order_index=1); db.add_all([user,year,level]); db.flush()
    cls=SchoolClass(school_id=school.id,academic_year_id=year.id,level_id=level.id,name="CE1 A",capacity=30); db.add(cls); db.commit()
    updated=update_class(cls.id,SchoolClassUpdate(name="CE1 B",capacity=35),db,user)
    assert updated.name == "CE1 B" and updated.capacity == 35
    assert deactivate_class(cls.id,db,user)["is_active"] is False
    e.dispose()


def test_class_cannot_be_deactivated_with_active_student():
    e, db = db_setup()
    school=School(name="Pilot",currency="XAF",language="fr"); db.add(school); db.flush()
    user=actor(school.id); year=AcademicYear(school_id=school.id,label="2026/2027",start_date=date(2026,9,1),end_date=date(2027,7,31),is_current=True); level=Level(school_id=school.id,name="CE1",order_index=1); db.add_all([user,year,level]); db.flush()
    cls=SchoolClass(school_id=school.id,academic_year_id=year.id,level_id=level.id,name="CE1 A"); student=Student(school_id=school.id,matricule="P1",first_name="A",last_name="B"); db.add_all([cls,student]); db.flush()
    db.add(ClassMembership(student_id=student.id,class_id=cls.id,academic_year_id=year.id,enrolled_at=date.today())); db.commit()
    with pytest.raises(HTTPException) as exc: deactivate_class(cls.id,db,user)
    assert exc.value.status_code == 409
    e.dispose()
