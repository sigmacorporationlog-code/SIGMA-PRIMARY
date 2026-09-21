from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models  # noqa
from app.core.database import Base
from app.models.organization import School
from app.models.security import User
from app.services.ai_knowledge import ingest_document, search, set_status, update_metadata


def test_governance_publishes_one_version_and_hides_drafts():
    e=create_engine('sqlite:///:memory:'); Base.metadata.create_all(e); s=sessionmaker(bind=e)()
    school=School(name='Gov School', currency='XAF', language='fr'); s.add(school); s.flush()
    u=User(school_id=school.id, username='gov', hashed_password='x', first_name='G', last_name='U'); s.add(u); s.commit()
    old=ingest_document(s,u,title='Procédure',content='Ancienne procédure absences et retards version 2025.',version='2025')
    new=ingest_document(s,u,title='Procédure',content='Nouvelle procédure absences justifiées version 2026.',version='2026',status='draft')
    assert search(s,u,'retards')
    assert search(s,u,'justifiées') == []
    update_metadata(s,u,new.id,folder='Règlements',tags=['absence','2026','absence'])
    set_status(s,u,new.id,'published'); s.refresh(old)
    assert old.status == 'archived' and old.is_active is False
    assert search(s,u,'justifiées')[0]['version'] == '2026'
    s.close(); e.dispose()
