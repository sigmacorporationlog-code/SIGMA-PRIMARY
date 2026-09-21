from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.models.legal import LegalDocument
from app.services.legal import seed_legal_documents, accept_document, legal_status, upsert_authorization

router = APIRouter(prefix='/api/legal', tags=['SIGMA Legal'])

@router.get('/documents')
def documents(db: Session = Depends(get_db)):
    return {'items':[{'id':d.id,'code':d.code,'version':d.version,'type':d.document_type,'title':d.title,'hash':d.content_hash,'effective_on':d.effective_on.isoformat(),'required':d.is_required} for d in seed_legal_documents(db)]}

@router.get('/documents/{document_id}')
def document(document_id:int, db:Session=Depends(get_db)):
    seed_legal_documents(db); d=db.get(LegalDocument, document_id)
    if not d: raise HTTPException(404,'Document juridique introuvable')
    return {'id':d.id,'code':d.code,'version':d.version,'type':d.document_type,'title':d.title,'content':d.content,'hash':d.content_hash,'effective_on':d.effective_on.isoformat()}

class Acceptance(BaseModel):
    document_id:int=Field(ge=1)
    representative_name:str|None=None
    representative_role:str|None=None

@router.post('/accept')
def accept(payload:Acceptance, request:Request, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    try:
        row=accept_document(db,current_user.school_id,current_user.id,payload.document_id,request.client.host if request.client else None,request.headers.get('user-agent'),payload.representative_name,payload.representative_role)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'id':row.id,'accepted_at':row.accepted_at.isoformat(),'document_id':row.legal_document_id}

@router.get('/status')
def status(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return legal_status(db,current_user.school_id,current_user.id)

class AuthorizationPayload(BaseModel):
    organization_name:str=Field(min_length=2,max_length=255)
    controller_name:str=Field(min_length=2,max_length=255)
    controller_email:str|None=None
    controller_phone:str|None=None
    purposes:str=Field(min_length=10)
    categories:str=Field(min_length=10)
    retention_policy:str=Field(min_length=10)
    authorized_on:str
    notes:str|None=None

@router.put('/authorization')
def authorization(payload:AuthorizationPayload, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(403,'Seul un superadministrateur peut enregistrer cette autorisation')
    from datetime import date
    try: authorized_on=date.fromisoformat(payload.authorized_on)
    except ValueError as exc: raise HTTPException(400,'authorized_on doit être YYYY-MM-DD') from exc
    row=upsert_authorization(db, {'school_id':current_user.school_id,'authorized_by_user_id':current_user.id, **payload.model_dump(exclude={'authorized_on'}), 'authorized_on':authorized_on, 'status':'active'})
    return {'id':row.id,'school_id':row.school_id,'status':row.status,'authorized_on':row.authorized_on.isoformat()}


@router.get('/acceptances')
def acceptances(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.legal import LegalAcceptance
    rows = db.query(LegalAcceptance).filter(LegalAcceptance.school_id == current_user.school_id, LegalAcceptance.user_id == current_user.id).order_by(LegalAcceptance.accepted_at.desc()).all()
    return {'items':[{'id':r.id,'document_id':r.legal_document_id,'code':r.document.code if r.document else None,'version':r.document.version if r.document else None,'accepted_at':r.accepted_at.isoformat(),'representative_name':r.representative_name,'representative_role':r.representative_role,'method':r.acceptance_method} for r in rows]}

@router.get('/authorization')
def get_authorization(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.legal import DataProcessingAuthorization
    row = db.query(DataProcessingAuthorization).filter(DataProcessingAuthorization.school_id == current_user.school_id).first()
    if not row:
        return {'exists': False, 'authorization': None}
    return {'exists': True, 'authorization': {'id':row.id,'school_id':row.school_id,'organization_name':row.organization_name,'controller_name':row.controller_name,'controller_email':row.controller_email,'controller_phone':row.controller_phone,'purposes':row.purposes,'categories':row.categories,'retention_policy':row.retention_policy,'authorized_on':row.authorized_on.isoformat(),'revoked_on':row.revoked_on.isoformat() if row.revoked_on else None,'status':row.status,'notes':row.notes}}

class AuthorizationRevocation(BaseModel):
    revoked_on:str
    notes:str|None=None

@router.post('/authorization/revoke')
def revoke_authorization(payload:AuthorizationRevocation, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(403,'Seul un superadministrateur peut révoquer cette autorisation')
    from app.models.legal import DataProcessingAuthorization
    from datetime import date
    row = db.query(DataProcessingAuthorization).filter(DataProcessingAuthorization.school_id == current_user.school_id).first()
    if not row:
        raise HTTPException(404,'Autorisation introuvable')
    try: row.revoked_on = date.fromisoformat(payload.revoked_on)
    except ValueError as exc: raise HTTPException(400,'revoked_on doit être YYYY-MM-DD') from exc
    row.status='revoked'; row.notes=payload.notes or row.notes
    db.commit(); db.refresh(row)
    return {'id':row.id,'status':row.status,'revoked_on':row.revoked_on.isoformat()}
