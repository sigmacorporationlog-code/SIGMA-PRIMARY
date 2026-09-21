from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin

class SubscriptionInvoice(Base, TimestampMixin):
    __tablename__ = 'subscription_invoices'
    __table_args__ = (UniqueConstraint('school_id', 'period_start', 'period_end', name='uq_subscription_invoice_period'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey('school_subscriptions.id'), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount_xaf: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='XAF', nullable=False)
    status: Mapped[str] = mapped_column(String(30), default='issued', nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class SubscriptionPayment(Base, TimestampMixin):
    __tablename__ = 'subscription_payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('subscription_invoices.id'), nullable=False, index=True)
    amount_xaf: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default='pending', nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_event_id: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True, index=True)
