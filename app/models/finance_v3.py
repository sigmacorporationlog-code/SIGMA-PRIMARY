from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin

class MobileMoneyConfiguration(Base, TimestampMixin):
    __tablename__ = 'mobile_money_configurations'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)  # mtn_momo / orange_money
    merchant_name: Mapped[str | None] = mapped_column(String(150))
    merchant_code: Mapped[str | None] = mapped_column(String(100))
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    credentials_ref: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = 'payment_transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey('payments.id'), nullable=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(150), unique=True)
    payer_phone: Mapped[str | None] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default='XAF', nullable=False)
    status: Mapped[str] = mapped_column(String(30), default='pending', nullable=False)
    # pending / initiated / succeeded / failed / cancelled / reconciled
    provider_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class FinanceReminder(Base, TimestampMixin):
    __tablename__ = 'finance_reminders'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default='queued', nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
