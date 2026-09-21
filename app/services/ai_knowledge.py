"""Base documentaire institutionnelle de SIGMA AI.

V4.13 ajoute une ingestion sûre de TXT/MD/PDF/DOCX, des métadonnées de
provenance (page/paragraphe), la gestion d'activation des versions et conserve
le cloisonnement strict par établissement.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_knowledge import AIKnowledgeChunk, AIKnowledgeDocument
from app.models.security import User

_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "et", "ou", "à", "a", "au", "aux",
    "en", "dans", "pour", "sur", "par", "avec", "ce", "cette", "ces", "est", "sont", "que", "qui",
    "quoi", "comment", "quelle", "quel", "quels", "quelles", "mon", "ma", "mes", "notre", "nos", "leur", "leurs",
}
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def normalize_tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "") if len(w) > 1 and w.lower() not in _STOPWORDS]


def content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def chunk_text(content: str, max_chars: int = 1800, overlap: int = 180) -> list[str]:
    text = re.sub(r"\r\n?", "\n", content or "").strip()
    if not text:
        return []
    if max_chars < 300 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Paramètres de découpage invalides")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = [paragraph[i:i + max_chars] for i in range(0, len(paragraph), max_chars)] or [paragraph]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                chunks.append(current.strip())
                tail = current[-overlap:] if overlap else ""
                current = f"{tail}\n{piece}".strip()
                if len(current) > max_chars:
                    current = piece
    if current:
        chunks.append(current.strip())
    return chunks


def _assert_school(user: User, school_id: int) -> None:
    if not user.is_superadmin and user.school_id != school_id:
        raise PermissionError("Périmètre établissement interdit")


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage texte non pris en charge")


def extract_uploaded_document(filename: str, raw: bytes) -> tuple[str, list[dict], str]:
    """Extrait le texte et ses métadonnées sans conserver le fichier original."""
    if not filename:
        raise ValueError("Nom de fichier requis")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Fichier limité à 15 Mo")
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Format non pris en charge. Utilisez TXT, MD, PDF ou DOCX.")
    if not raw:
        raise ValueError("Fichier vide")

    pages: list[dict] = []
    if ext in {".txt", ".md"}:
        text = _decode_text(raw)
        pages = [{"source_unit": "document", "source_index": 1, "text": text}]
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            for idx, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"source_unit": "page", "source_index": idx, "text": text})
        except Exception as exc:
            raise ValueError(f"PDF illisible ou protégé : {exc}") from exc
        if not pages:
            raise ValueError("Aucun texte extractible dans le PDF. Un PDF scanné nécessite un OCR.")
    else:  # docx
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if not paragraphs:
                raise ValueError("Aucun texte extractible dans le DOCX")
            pages = [{"source_unit": "paragraph", "source_index": i, "text": text}
                     for i, text in enumerate(paragraphs, 1)]
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"DOCX illisible : {exc}") from exc

    combined = "\n\n".join(item["text"] for item in pages).strip()
    if len(combined) < 20:
        raise ValueError("Le contenu extrait est trop court")
    return combined, pages, ext[1:]


def _chunk_with_metadata(pages: list[dict], max_chars: int = 1800, overlap: int = 180) -> list[tuple[str, dict]]:
    """Découpe en conservant une provenance approximative page/paragraphe."""
    result: list[tuple[str, dict]] = []
    for page in pages:
        pieces = chunk_text(page["text"], max_chars=max_chars, overlap=overlap)
        for local_index, piece in enumerate(pieces):
            result.append((piece, {"source_unit": page["source_unit"], "source_index": page["source_index"],
                                   "local_chunk_index": local_index}))
    return result


def ingest_document(db: Session, user: User, *, title: str, content: str, document_type: str = "internal",
                    version: str | None = None, source_name: str | None = None,
                    metadata: dict | None = None, source_units: list[dict] | None = None,
                    folder: str = "General", tags: list[str] | None = None, status: str = "published",
                    extraction_method: str | None = None) -> AIKnowledgeDocument:
    school_id = user.school_id
    if not title.strip() or len(title) > 255:
        raise ValueError("Titre de document invalide")
    if len(content or "") < 20:
        raise ValueError("Le contenu du document est trop court")
    if status not in {"draft", "review", "published", "archived"}:
        raise ValueError("Statut documentaire invalide")
    folder = (folder or "General").strip()[:120]
    clean_tags = list(dict.fromkeys(str(t).strip()[:50] for t in (tags or []) if str(t).strip()))[:30]
    if len(content) > 500_000:
        raise ValueError("Document limité à 500 000 caractères")
    h = content_hash(content)
    existing = db.scalar(select(AIKnowledgeDocument).where(
        AIKnowledgeDocument.school_id == school_id, AIKnowledgeDocument.content_hash == h))
    if existing:
        return existing
    chunks_with_meta = _chunk_with_metadata(source_units or [{"source_unit": "document", "source_index": 1, "text": content}])
    now = datetime.now(timezone.utc)
    doc = AIKnowledgeDocument(school_id=school_id, title=title.strip(), document_type=document_type[:60],
                              version=(version[:80] if version else None), source_name=(source_name[:255] if source_name else None),
                              content_hash=h, content_length=len(content), chunk_count=len(chunks_with_meta), is_active=True,
                              created_at=now, updated_at=now, metadata_json=metadata or {}, folder=folder or "General",
                              tags_json=clean_tags, status=status, extraction_method=extraction_method,
                              published_at=(now if status == "published" else None),
                              approved_by_user_id=(user.id if status == "published" else None),
                              approved_at=(now if status == "published" else None))
    db.add(doc); db.flush()
    for idx, (chunk, chunk_meta) in enumerate(chunks_with_meta):
        db.add(AIKnowledgeChunk(school_id=school_id, document_id=doc.id, chunk_index=idx,
                                content=chunk, token_count=len(normalize_tokens(chunk)), metadata_json=chunk_meta))
    db.commit(); db.refresh(doc)
    return doc


def list_documents(db: Session, user: User, school_id: int | None = None, *, include_inactive: bool = False) -> list[AIKnowledgeDocument]:
    if school_id is not None:
        _assert_school(user, school_id); target = school_id
    else:
        target = user.school_id
        if target is None: raise ValueError("Un établissement doit être sélectionné")
    stmt = select(AIKnowledgeDocument).where(AIKnowledgeDocument.school_id == target)
    if not include_inactive:
        stmt = stmt.where(AIKnowledgeDocument.is_active.is_(True))
    return list(db.scalars(stmt.order_by(AIKnowledgeDocument.updated_at.desc())).all())


def set_active(db: Session, user: User, document_id: int, active: bool) -> AIKnowledgeDocument:
    doc = db.get(AIKnowledgeDocument, document_id)
    if not doc: raise ValueError("Document introuvable")
    _assert_school(user, doc.school_id)
    now = datetime.now(timezone.utc)
    if active:
        # Une seule version publiée/active par titre et établissement.
        siblings = db.scalars(select(AIKnowledgeDocument).where(
            AIKnowledgeDocument.school_id == doc.school_id,
            AIKnowledgeDocument.title == doc.title,
            AIKnowledgeDocument.id != doc.id)).all()
        for sibling in siblings:
            sibling.is_active = False
        doc.status = "published"
        doc.approved_by_user_id = user.id
        doc.approved_at = now
        doc.published_at = doc.published_at or now
    else:
        doc.status = "archived"
    doc.is_active = active
    doc.updated_at = now
    db.commit(); db.refresh(doc)
    return doc


def search(db: Session, user: User, query: str, *, limit: int = 5, school_id: int | None = None) -> list[dict]:
    query_tokens = set(normalize_tokens(query))
    if not query_tokens: return []
    if school_id is not None:
        _assert_school(user, school_id); target = school_id
    else:
        target = user.school_id
        if target is None: raise ValueError("Un établissement doit être sélectionné")
    chunks = db.scalars(select(AIKnowledgeChunk).join(AIKnowledgeDocument, AIKnowledgeDocument.id == AIKnowledgeChunk.document_id).where(
        AIKnowledgeChunk.school_id == target, AIKnowledgeDocument.school_id == target,
        AIKnowledgeDocument.is_active.is_(True), AIKnowledgeDocument.status == "published")).all()
    # Retrieval hybride sans dépendance à un moteur vectoriel : BM25-like lexical
    # + bonus titre/tags/phrase. Cela reste déterministe et compatible SQLite.
    doc_freq = {}
    token_sets = {}
    for c in chunks:
        toks = set(normalize_tokens(c.content)); token_sets[c.id] = toks
        for tok in toks: doc_freq[tok] = doc_freq.get(tok, 0) + 1
    import math
    N = max(1, len(chunks))
    ranked = []
    qtext = query.lower().strip()
    for chunk in chunks:
        toks = token_sets[chunk.id]; overlap = query_tokens & toks
        if not overlap: continue
        idf = sum(math.log((N + 1) / (doc_freq.get(t, 0) + 1)) + 1 for t in overlap)
        doc = db.get(AIKnowledgeDocument, chunk.document_id)
        title_tokens = set(normalize_tokens(doc.title))
        tag_tokens = set(normalize_tokens(" ".join(doc.tags_json or [])))
        title_bonus = 0.35 * len(query_tokens & title_tokens)
        tag_bonus = 0.20 * len(query_tokens & tag_tokens)
        phrase_bonus = 0.30 if qtext in chunk.content.lower() else 0
        score = min(1.0, (idf / max(1, len(query_tokens) * 2.5)) + title_bonus + tag_bonus + phrase_bonus)
        ranked.append((score, chunk, doc))
    ranked.sort(key=lambda x: (-x[0], x[1].document_id, x[1].chunk_index))
    out = []
    for score, chunk, doc in ranked[:max(1, min(limit, 20))]:
        meta = chunk.metadata_json or {}
        location = f"{meta.get('source_unit')} {meta.get('source_index')}" if meta.get('source_unit') else f"section {chunk.chunk_index + 1}"
        citation = f"{doc.title}{(' — v' + doc.version) if doc.version else ''}, {location}"
        out.append({"school_id": target, "document_id": doc.id, "title": doc.title, "document_type": doc.document_type,
                    "version": doc.version, "source_name": doc.source_name, "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index, "score": round(score, 4), "content": chunk.content,
                    "metadata": meta, "citation": citation})
    return out


def update_metadata(db: Session, user: User, document_id: int, *, folder: str | None = None, tags: list[str] | None = None) -> AIKnowledgeDocument:
    doc = db.get(AIKnowledgeDocument, document_id)
    if not doc: raise ValueError("Document introuvable")
    _assert_school(user, doc.school_id)
    if folder is not None:
        doc.folder = folder.strip()[:120] or "General"
    if tags is not None:
        doc.tags_json = list(dict.fromkeys(str(t).strip()[:50] for t in tags if str(t).strip()))[:30]
    doc.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(doc)
    return doc


def set_status(db: Session, user: User, document_id: int, status: str) -> AIKnowledgeDocument:
    doc = db.get(AIKnowledgeDocument, document_id)
    if not doc: raise ValueError("Document introuvable")
    _assert_school(user, doc.school_id)
    if status not in {"draft", "review", "published", "archived"}: raise ValueError("Statut documentaire invalide")
    now = datetime.now(timezone.utc)
    if status == "published":
        siblings = db.scalars(select(AIKnowledgeDocument).where(AIKnowledgeDocument.school_id == doc.school_id, AIKnowledgeDocument.title == doc.title, AIKnowledgeDocument.id != doc.id)).all()
        for sibling in siblings:
            sibling.is_active = False
            sibling.status = "archived"
        doc.is_active = True
        doc.approved_by_user_id = user.id
        doc.approved_at = now
        doc.published_at = now
    else:
        doc.is_active = False
    doc.status = status
    doc.updated_at = now
    db.commit(); db.refresh(doc)
    return doc
