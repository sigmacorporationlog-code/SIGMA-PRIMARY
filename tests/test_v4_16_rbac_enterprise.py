from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from fastapi import HTTPException

from app.core.database import Base
from app.models.organization import School
from app.models.security import User, Permission, Post, PostPermission, UserPost
from app.services.rbac_enterprise import ensure_profile, assign_profile, profile_catalog, ROLE_PROFILES


def db_setup():
    e = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    school = School(name='RBAC School', currency='XAF', language='fr'); s.add(school); s.flush()
    codes = ROLE_PROFILES['administration']['permissions']
    perms = [Permission(code=c, module=c.split('.')[0], label=c) for c in codes]
    s.add_all(perms); s.flush()
    actor = User(school_id=school.id, username='actor', hashed_password='x', first_name='A', last_name='A')
    target = User(school_id=school.id, username='target', hashed_password='x', first_name='T', last_name='T')
    s.add_all([actor, target]); s.flush()
    # Depuis le durcissement v4.61, nul ne peut déléguer une permission qu'il ne
    # détient pas lui-même de façon non restreinte : l'acteur reçoit donc le
    # poste correspondant avant de pouvoir attribuer le profil.
    post = Post(school_id=school.id, name='Direction générale'); s.add(post); s.flush()
    for perm in perms:
        s.add(PostPermission(post_id=post.id, permission_id=perm.id, scope={}))
    s.add(UserPost(user_id=actor.id, post_id=post.id))
    s.commit()
    return e, s, actor, target


def test_profile_catalog_is_explicit():
    codes = {x['code'] for x in profile_catalog()}
    assert {'direction','administration','enseignant','comptabilite','lecture_seule'} <= codes


def test_assign_profile_creates_post_and_membership():
    e,s,actor,target = db_setup()
    post = assign_profile(s, actor, target.id, 'administration')
    assert post.name == 'Administration scolaire'
    assert s.query(UserPost).filter_by(user_id=target.id, post_id=post.id).count() == 1
    e.dispose()


def test_cross_school_assignment_is_rejected():
    e,s,actor,target = db_setup()
    other = School(name='Other', currency='XAF', language='fr'); s.add(other); s.flush()
    foreign = User(school_id=other.id, username='foreign', hashed_password='x', first_name='F', last_name='F'); s.add(foreign); s.commit()
    with pytest.raises(HTTPException) as exc:
        assign_profile(s, actor, foreign.id, 'administration')
    assert exc.value.status_code == 403
    e.dispose()
