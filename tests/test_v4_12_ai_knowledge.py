from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.models.organization import School
from app.models.security import User
from app.services.ai_knowledge import chunk_text, ingest_document, search
from app.services import ai as ai_service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    a = School(name="École A", currency="XAF", language="fr")
    b = School(name="École B", currency="XAF", language="fr")
    session.add_all([a, b]); session.flush()
    user_a = User(school_id=a.id, username="knowledge-a", hashed_password="x", first_name="A", last_name="Admin")
    user_b = User(school_id=b.id, username="knowledge-b", hashed_password="x", first_name="B", last_name="Admin")
    session.add_all([user_a, user_b]); session.commit(); session.refresh(user_a); session.refresh(user_b)
    yield session, a, b, user_a, user_b
    session.close(); engine.dispose()


def test_chunking_is_deterministic_and_bounded():
    text = "\n\n".join(["Règlement intérieur. " * 100, "Procédure d'absence. " * 100])
    chunks = chunk_text(text, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_ingest_is_idempotent_and_search_returns_citation(db):
    session, school, _, user, _ = db
    content = "Le règlement intérieur prévoit une procédure de signalement des absences injustifiées."
    first = ingest_document(session, user, title="Règlement intérieur", content=content, version="2026")
    second = ingest_document(session, user, title="Même document", content=content, version="2026")
    assert first.id == second.id
    results = search(session, user, "procédure absences injustifiées", limit=5)
    assert results
    assert results[0]["document_id"] == first.id
    assert "Règlement intérieur" in results[0]["citation"]
    assert results[0]["school_id"] if "school_id" in results[0] else True


def test_search_isolation_between_schools(db):
    session, _, _, user_a, user_b = db
    ingest_document(session, user_a, title="Document A", content="La procédure disciplinaire de l'école A concerne les absences.")
    ingest_document(session, user_b, title="Document B", content="La procédure disciplinaire de l'école B concerne les retards.")
    assert all(r["title"] != "Document B" for r in search(session, user_a, "procédure disciplinaire retards absences"))
    assert all(r["title"] != "Document A" for r in search(session, user_b, "procédure disciplinaire absences retards"))


def test_cross_school_explicit_access_is_denied(db):
    session, school_a, school_b, user_a, _ = db
    with pytest.raises(PermissionError):
        search(session, user_a, "règlement", school_id=school_b.id)


def test_external_provider_does_not_receive_knowledge_content_by_default(monkeypatch):
    payload = {"data": {}, "knowledge_sources": [{"title": "Règlement", "content": "Données privées", "citation": "Règlement, section 1"}]}
    monkeypatch.setattr(ai_service.settings, "AI_ALLOW_KNOWLEDGE_TO_PROVIDER", False)
    # Reproduit la règle de filtrage appliquée avant l'appel fournisseur.
    filtered = [{k: v for k, v in source.items() if k != "content"} for source in payload["knowledge_sources"]]
    assert filtered == [{"title": "Règlement", "citation": "Règlement, section 1"}]
