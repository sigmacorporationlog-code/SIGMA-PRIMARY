from __future__ import annotations
from datetime import date, datetime, timezone
from hashlib import sha256
from sqlalchemy.orm import Session
from app.models.legal import LegalDocument, LegalAcceptance, DataProcessingAuthorization

REQUIRED_CODES = ('SIGMA-LICENCE', 'SIGMA-PRIVACY', 'SIGMA-AUTHORIZATION')

def content_hash(content: str) -> str:
    return sha256(content.encode('utf-8')).hexdigest()

def seed_legal_documents(db: Session) -> list[LegalDocument]:
    docs = []
    from app.legal.documents import LEGAL_DOCUMENTS
    for item in LEGAL_DOCUMENTS:
        existing = db.query(LegalDocument).filter(LegalDocument.code == item['code'], LegalDocument.version == item['version']).first()
        if existing:
            docs.append(existing); continue
        doc = LegalDocument(**item, content_hash=content_hash(item['content']))
        db.add(doc); docs.append(doc)
    db.commit()
    for d in docs: db.refresh(d)
    return docs

def accept_document(db: Session, school_id: int, user_id: int, document_id: int, ip_address: str | None, user_agent: str | None, representative_name: str | None, representative_role: str | None) -> LegalAcceptance:
    doc = db.get(LegalDocument, document_id)
    if not doc or not doc.is_active:
        raise ValueError('Document juridique introuvable ou inactif')
    existing = db.query(LegalAcceptance).filter(LegalAcceptance.school_id == school_id, LegalAcceptance.user_id == user_id, LegalAcceptance.legal_document_id == document_id).first()
    if existing: return existing
    row = LegalAcceptance(school_id=school_id, user_id=user_id, legal_document_id=document_id, accepted_at=datetime.now(timezone.utc), ip_address=ip_address, user_agent=user_agent, representative_name=representative_name, representative_role=representative_role, declaration='Je déclare avoir lu, compris et accepté le document dans sa version indiquée.')
    db.add(row); db.commit(); db.refresh(row)
    return row

def legal_status(db: Session, school_id: int, user_id: int) -> dict:
    docs = [d for d in seed_legal_documents(db) if d.code in REQUIRED_CODES and d.is_active]
    accepted = {a.legal_document_id for a in db.query(LegalAcceptance).filter(LegalAcceptance.school_id == school_id, LegalAcceptance.user_id == user_id).all()}
    items = [{'id': d.id, 'code': d.code, 'version': d.version, 'title': d.title, 'required': d.is_required, 'accepted': d.id in accepted, 'effective_on': d.effective_on.isoformat()} for d in docs]
    return {'school_id': school_id, 'user_id': user_id, 'complete': all(x['accepted'] for x in items if x['required']), 'documents': items}

def upsert_authorization(db: Session, payload: dict) -> DataProcessingAuthorization:
    row = db.query(DataProcessingAuthorization).filter(DataProcessingAuthorization.school_id == payload['school_id']).first()
    if row:
        for k,v in payload.items():
            if k != 'school_id': setattr(row,k,v)
    else:
        row = DataProcessingAuthorization(**payload); db.add(row)
    db.commit(); db.refresh(row); return row
