from datetime import date, timedelta, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.database import Base
from app.models.organization import School
from app.models.security import Delegation, Permission, Post, PostPermission, User, UserPost
from app.models.operations_v4 import PlatformIncident
from app.services.authorization import user_has_permission
from app.services.operations_v4 import resolve_incident
from app.services.rate_limit import InMemoryRateLimiter, RateLimitExceeded


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_authorization_rejects_cross_tenant_post_assignment():
    db = setup_db()
    school_a = School(name="A", currency="XAF", language="fr")
    school_b = School(name="B", currency="XAF", language="fr")
    db.add_all([school_a, school_b])
    db.flush()
    user = User(school_id=school_a.id, username="u", hashed_password="x", first_name="U", last_name="A")
    post = Post(school_id=school_b.id, name="Foreign post")
    permission = Permission(code="security.test", module="security", label="Test")
    db.add_all([user, post, permission])
    db.flush()
    db.add(UserPost(user_id=user.id, post_id=post.id))
    db.add(PostPermission(post_id=post.id, permission_id=permission.id, scope={}))
    db.commit()

    assert not user_has_permission(db, user, "security.test")


def test_authorization_rejects_cross_tenant_delegation():
    db = setup_db()
    school_a = School(name="A", currency="XAF", language="fr")
    school_b = School(name="B", currency="XAF", language="fr")
    db.add_all([school_a, school_b])
    db.flush()
    user = User(school_id=school_a.id, username="u2", hashed_password="x", first_name="U", last_name="B")
    permission = Permission(code="security.test2", module="security", label="Test")
    db.add_all([user, permission])
    db.flush()
    db.add(Delegation(
        school_id=school_b.id,
        granted_by_id=user.id,
        granted_to_id=user.id,
        permission_id=permission.id,
        scope={},
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
    ))
    db.commit()

    assert not user_has_permission(db, user, "security.test2")


def test_resolve_incident_checks_tenant_before_mutation():
    db = setup_db()
    school_a = School(name="A", currency="XAF", language="fr")
    school_b = School(name="B", currency="XAF", language="fr")
    db.add_all([school_a, school_b])
    db.flush()
    actor = User(school_id=school_a.id, username="actor", hashed_password="x", first_name="A", last_name="C")
    db.add(actor)
    db.flush()
    incident = PlatformIncident(
        school_id=school_b.id, severity="high", status="open", category="security", title="Tenant isolation", detected_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    db.commit()

    with pytest.raises(PermissionError):
        resolve_incident(db, incident.id, actor)

    db.refresh(incident)
    assert incident.status == "open"
    assert incident.resolved_at is None


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()
    for _ in range(2):
        limiter.check("ip", limit=2, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        limiter.check("ip", limit=2, window_seconds=60)
