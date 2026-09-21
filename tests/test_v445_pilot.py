from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa
from app.core.database import Base
from app.models.organization import School
from app.services.pilot import pilot_readiness


def setup_db():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return sessionmaker(bind=e)()


def test_pilot_readiness_for_missing_school():
    db = setup_db()
    try:
        pilot_readiness(db, 999999)
    except ValueError as exc:
        assert "introuvable" in str(exc)
    else:
        raise AssertionError("missing school must fail")


def test_pilot_readiness_reports_school_state():
    db = setup_db()
    school = School(name="École Pilote", currency="XAF", language="fr")
    db.add(school)
    db.flush()
    result = pilot_readiness(db, school.id)
    assert result["school_id"] == school.id
    assert result["ready_for_pilot"] is False
    assert result["counts"]["students"] == 0
    assert result["checks"]["school_configured"] is True
    assert result["checks"]["academic_year"] is False
