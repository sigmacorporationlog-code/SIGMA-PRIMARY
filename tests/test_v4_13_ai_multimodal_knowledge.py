from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.models.organization import School
from app.models.security import User
from app.services.ai_knowledge import extract_uploaded_document, ingest_document, search, set_active


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    a = School(name="École A", currency="XAF", language="fr")
    b = School(name="École B", currency="XAF", language="fr")
    s.add_all([a, b]); s.flush()
    ua = User(school_id=a.id, username="v413-a", hashed_password="x", first_name="A", last_name="Admin")
    ub = User(school_id=b.id, username="v413-b", hashed_password="x", first_name="B", last_name="Admin")
    s.add_all([ua, ub]); s.commit()
    yield s, a, b, ua, ub
    s.close(); engine.dispose()


def test_txt_upload_extracts_provenance():
    text, units, kind = extract_uploaded_document("reglement.md", "Règlement intérieur\n\nAbsences et retards.".encode())
    assert kind == "md"
    assert "Absences" in text
    assert units[0]["source_unit"] == "document"


def test_rejects_unsupported_and_oversized():
    with pytest.raises(ValueError): extract_uploaded_document("photo.jpg", b"x" * 30)


def test_activation_isolation_and_versioning(db):
    s, a, _, ua, _ = db
    old = ingest_document(s, ua, title="Règlement", content="Règlement version ancienne : absences et retards.", version="2025")
    new = ingest_document(s, ua, title="Règlement", content="Règlement version nouvelle : absences justifiées.", version="2026")
    assert old.is_active and new.is_active
    set_active(s, ua, new.id, True)
    s.refresh(old)
    assert old.is_active is False and new.is_active is True
    assert search(s, ua, "retards", limit=10) == []
    assert search(s, ua, "absences justifiées", limit=10)[0]["version"] == "2026"
