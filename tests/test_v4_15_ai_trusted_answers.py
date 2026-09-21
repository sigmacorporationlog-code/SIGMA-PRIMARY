from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.models import School
from app.models.security import User
from app.services.ai_knowledge import ingest_document
from app.services import ai


def setup_db():
    from app.core.database import Base
    e=create_engine('sqlite:///:memory:'); Base.metadata.create_all(e); s=sessionmaker(bind=e)()
    school=School(name='Trusted School', currency='XAF', language='fr'); s.add(school); s.flush()
    u=User(school_id=school.id, username='trusted', hashed_password='x', first_name='T', last_name='U'); s.add(u); s.commit()
    return e,s,u


def test_knowledge_search_returns_citation_and_score():
    e,s,u=setup_db()
    ingest_document(s,u,title='Règlement intérieur',content='Les retards répétés doivent être signalés à la direction.',version='2026')
    result=ai.knowledge_search(s,u,'retards répétés')
    assert result and result[0]['citation'].startswith('Règlement intérieur — v2026')
    assert 0 <= result[0]['score'] <= 1
    s.close(); e.dispose()


def test_grounded_document_question_refuses_when_no_source(monkeypatch):
    e,s,u=setup_db()
    monkeypatch.setattr(ai.settings, 'AI_PROVIDER', 'local')
    monkeypatch.setattr(ai.settings, 'AI_GROUNDED_ONLY', True)
    monkeypatch.setattr(ai, 'user_has_permission', lambda db, user, permission: True)
    with pytest.raises(RuntimeError, match='Aucune source documentaire'):
        ai.ask(s,u,'Que dit le règlement sur les sorties scolaires ?')
    s.close(); e.dispose()
