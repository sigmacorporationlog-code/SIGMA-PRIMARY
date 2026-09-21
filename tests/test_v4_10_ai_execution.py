from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.models.ai_actions import AIActionProposal
from app.models.organization import School
from app.models.security import User
from app.models.students import Student
from app.services import ai_actions


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    school = School(name="École Test", currency="XAF", language="fr")
    session.add(school); session.flush()
    yield session, school
    session.close(); engine.dispose()


@pytest.fixture
def superadmin(db):
    session, school = db
    user = User(school_id=school.id, username="admin-test", hashed_password="x", first_name="Admin", last_name="Test", is_superadmin=True)
    session.add(user); session.commit(); session.refresh(user)
    return user


def test_execution_disabled_is_safe(db, superadmin):
    session, school = db
    proposal = AIActionProposal(
        school_id=school.id, created_by_user_id=superadmin.id, action_type="report_generation",
        title="Rapport", payload_json={}, status="approved", created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), result_json={}, execution_key="test-exec-disabled",
    )
    session.add(proposal); session.commit(); session.refresh(proposal)
    with pytest.raises(RuntimeError):
        ai_actions.execute(session, superadmin, proposal.id)


def test_execute_report_is_idempotent(db, superadmin, monkeypatch, tmp_path):
    session, school = db
    monkeypatch.setattr(ai_actions.settings, "AI_ACTION_EXECUTION_ENABLED", True)
    monkeypatch.setattr(ai_actions, "data_dir", lambda: tmp_path)
    session.add(Student(school_id=school.id, matricule="S001", first_name="A", last_name="Test", status="active"))
    proposal = AIActionProposal(
        school_id=school.id, created_by_user_id=superadmin.id, action_type="report_generation",
        title="Rapport", payload_json={}, status="approved", created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), result_json={}, execution_key="test-exec-idempotent",
    )
    session.add(proposal); session.commit(); session.refresh(proposal)
    first = ai_actions.execute(session, superadmin, proposal.id)
    assert first.status == "executed"
    path = first.result_json["file_path"]
    second = ai_actions.execute(session, superadmin, proposal.id)
    assert second.status == "executed"
    assert second.result_json["file_path"] == path
