from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.models.ai_actions import AIActionProposal
from app.models.organization import School
from app.models.security import User
from app.services import ai_actions


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    school_a = School(name="École A", currency="XAF", language="fr")
    school_b = School(name="École B", currency="XAF", language="fr")
    session.add_all([school_a, school_b]); session.flush()
    user = User(school_id=school_a.id, username="ai-control", hashed_password="x", first_name="Admin", last_name="A", is_superadmin=True)
    session.add(user); session.commit(); session.refresh(user)
    yield session, school_a, school_b, user
    session.close(); engine.dispose()


def test_control_center_counts_all_and_limits_recent(db):
    session, a, b, user = db
    now = datetime.now(timezone.utc)
    for i, status in enumerate(["proposed", "approved", "executed", "rejected", "expired", "proposed"]):
        session.add(AIActionProposal(school_id=a.id, created_by_user_id=user.id, action_type="report_generation", title=f"A{i}", status=status, created_at=now - timedelta(minutes=i), expires_at=now + timedelta(hours=1), payload_json={}, result_json={}, execution_key=f"key-a-{i}"))
    other = User(school_id=b.id, username="b", hashed_password="x", first_name="B", last_name="User")
    session.add(other); session.flush()
    session.add(AIActionProposal(school_id=b.id, created_by_user_id=other.id, action_type="report_generation", title="B", status="proposed", created_at=now, expires_at=now + timedelta(hours=1), payload_json={}, result_json={}, execution_key="key-b"))
    session.commit()
    result = ai_actions.control_center(session, user, limit=2)
    assert result["counts"]["proposed"] == 3
    assert sum(result["counts"].values()) == 7
    assert len(result["proposals"]) == 2
    assert len({item.school_id for item in result["proposals"]}) == 2
