from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.mixins import TimestampMixin

class LegalDocument(Base, TimestampMixin):
    __tablename__ = 'legal_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # license/privacy/authorization
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    effective_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint('code', 'version', name='uq_legal_document_version'),)

class LegalAcceptance(Base, TimestampMixin):
    __tablename__ = 'legal_acceptances'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    legal_document_id: Mapped[int] = mapped_column(ForeignKey('legal_documents.id'), nullable=False, index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    representative_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representative_role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    acceptance_method: Mapped[str] = mapped_column(String(50), default='electronic_checkbox', nullable=False)
    declaration: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[LegalDocument] = relationship()
    __table_args__ = (UniqueConstraint('school_id', 'legal_document_id', 'user_id', name='uq_legal_acceptance_school_doc_user'),)

class DataProcessingAuthorization(Base, TimestampMixin):
    __tablename__ = 'data_processing_authorizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False, unique=True, index=True)
    authorized_by_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    controller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    controller_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    controller_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    purposes: Mapped[str] = mapped_column(Text, nullable=False)
    categories: Mapped[str] = mapped_column(Text, nullable=False)
    retention_policy: Mapped[str] = mapped_column(Text, nullable=False)
    authorized_on: Mapped[date] = mapped_column(Date, nullable=False)
    revoked_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='active', nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
