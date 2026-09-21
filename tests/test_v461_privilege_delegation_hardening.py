from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.organization import School
from app.models.security import Delegation, Permission, Post, PostPermission, User, UserPost
from app.services.authorization import user_can_grant_permission
from app.services.rbac_enterprise import assign_profile


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_scoped_or_delegated_permission_cannot_be_used_as_privilege_escalation():
    db = setup_db()
    school = School(name="A", currency="XAF", language="fr")
    db.add(school); db.flush()
    p_users = Permission(code="administration.users.modify", module="administration", label="users")
    p_system = Permission(code="administration.system.view", module="administration", label="system")
    db.add_all([p_users, p_system]); db.flush()
    actor = User(school_id=school.id, username="actor", hashed_password="x", first_name="A", last_name="A")
    target = User(school_id=school.id, username="target", hashed_password="x", first_name="T", last_name="T")
    post = Post(school_id=school.id, name="Scoped admin")
    db.add_all([actor, target, post]); db.flush()
    db.add(PostPermission(post_id=post.id, permission_id=p_users.id, scope={"class_id": 10}))
    db.add(UserPost(user_id=actor.id, post_id=post.id)); db.commit()

    assert not user_can_grant_permission(db, actor, "administration.users.modify")
    with pytest.raises(HTTPException) as exc:
        assign_profile(db, actor, target.id, "administration")
    assert exc.value.status_code == 403


def test_direct_broad_permission_can_be_granted_but_delegation_chain_cannot():
    db = setup_db()
    school = School(name="B", currency="XAF", language="fr")
    db.add(school); db.flush()
    perm = Permission(code="students.view", module="students", label="view")
    db.add(perm); db.flush()
    actor = User(school_id=school.id, username="actor2", hashed_password="x", first_name="A", last_name="B")
    target = User(school_id=school.id, username="target2", hashed_password="x", first_name="T", last_name="B")
    post = Post(school_id=school.id, name="Viewer")
    db.add_all([actor, target, post]); db.flush()
    db.add_all([
        PostPermission(post_id=post.id, permission_id=perm.id, scope={}),
        UserPost(user_id=actor.id, post_id=post.id),
    ])
    db.commit()
    assert user_can_grant_permission(db, actor, "students.view")

    delegated = Delegation(
        school_id=school.id, granted_by_id=actor.id, granted_to_id=target.id,
        permission_id=perm.id, scope={}, start_date=date.today(),
        end_date=date.today() + timedelta(days=1), reason="test",
    )
    db.add(delegated); db.commit()
    assert user_can_grant_permission(db, target, "students.view") is False
