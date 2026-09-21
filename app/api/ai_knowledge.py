from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services import ai_knowledge
from app.services.authorization import user_has_permission

AI_PERMISSION = "administration.ai.use"
AI_GOVERN_PERMISSION = "administration.ai.execute"
router = APIRouter(prefix="/api/ai/knowledge", tags=["SIGMA AI Knowledge"])


class KnowledgeIngest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=20, max_length=500_000)
    document_type: str = Field(default="internal", max_length=60)
    version: str | None = Field(default=None, max_length=80)
    source_name: str | None = Field(default=None, max_length=255)
    folder: str = Field(default="General", max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=30)
    metadata: dict = Field(default_factory=dict)


class KnowledgeSearch(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeState(BaseModel):
    active: bool


class KnowledgeGovernance(BaseModel):
    status: str | None = None
    folder: str | None = Field(default=None, max_length=120)
    tags: list[str] | None = None


def _allowed(db: Session, user: User, permission: str = AI_PERMISSION) -> None:
    if not user_has_permission(db, user, permission):
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{permission}'")


def _out(doc):
    return {"id": doc.id, "title": doc.title, "document_type": doc.document_type, "version": doc.version,
            "source_name": doc.source_name, "content_hash": doc.content_hash, "chunk_count": doc.chunk_count,
            "content_length": doc.content_length, "is_active": doc.is_active, "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(), "metadata": doc.metadata_json or {},
            "folder": doc.folder, "tags": doc.tags_json or [], "status": doc.status,
            "approved_by_user_id": doc.approved_by_user_id, "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
            "published_at": doc.published_at.isoformat() if doc.published_at else None, "extraction_method": doc.extraction_method}


@router.post("/documents")
def ingest(payload: KnowledgeIngest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user)
    try:
        return _out(ai_knowledge.ingest_document(db, current_user, title=payload.title, content=payload.content,
            document_type=payload.document_type, version=payload.version, source_name=payload.source_name, metadata=payload.metadata, folder=payload.folder, tags=payload.tags))
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), title: str | None = Form(None), document_type: str = Form("internal"),
                          version: str | None = Form(None), folder: str = Form("General"), tags: str = Form(""), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user)
    try:
        raw = await file.read(ai_knowledge.MAX_UPLOAD_BYTES + 1)
        content, units, detected_type = ai_knowledge.extract_uploaded_document(file.filename or "", raw)
        final_title = (title or (file.filename or "Document")).strip()
        metadata = {"ingestion": "upload", "filename": file.filename, "content_type": file.content_type,
                    "format": detected_type, "unit_count": len(units)}
        doc = ai_knowledge.ingest_document(db, current_user, title=final_title, content=content,
            document_type=document_type, version=version, source_name=file.filename, metadata=metadata, source_units=units, folder=folder, tags=[t.strip() for t in tags.split(",") if t.strip()], extraction_method=f"upload_{detected_type}")
        return _out(doc)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/documents")
def documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user)
    return [_out(d) for d in ai_knowledge.list_documents(db, current_user, include_inactive=True)]


@router.post("/documents/{document_id}/state")
def state(document_id: int, payload: KnowledgeState, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user, AI_GOVERN_PERMISSION)
    try: return _out(ai_knowledge.set_active(db, current_user, document_id, payload.active))
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/documents/{document_id}/governance")
def governance(document_id: int, payload: KnowledgeGovernance, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user, AI_GOVERN_PERMISSION)
    try:
        doc = ai_knowledge.update_metadata(db, current_user, document_id, folder=payload.folder, tags=payload.tags)
        if payload.status is not None:
            doc = ai_knowledge.set_status(db, current_user, document_id, payload.status)
        return _out(doc)
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search")
def search(payload: KnowledgeSearch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _allowed(db, current_user)
    try: return {"results": ai_knowledge.search(db, current_user, payload.query, limit=payload.limit)}
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
