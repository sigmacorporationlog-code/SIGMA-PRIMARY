from datetime import date, datetime

from decimal import Decimal

from sqlalchemy import String, ForeignKey, Numeric, Date, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class FeeStructure(Base, TimestampMixin, SoftDeleteMixin):
    """Grille de frais (inscription, scolarité, cantine, transport...) pour une année/niveau."""

    __tablename__ = "fee_structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    level_id: Mapped[int | None] = mapped_column(ForeignKey("levels.id"), nullable=True)
    fee_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # registration / tuition / canteen / transport / uniform / exam / activity / other
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class Invoice(Base, TimestampMixin):
    """Facture d'un élève, générée à partir de sa grille de frais."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    fee_structure_id: Mapped[int] = mapped_column(ForeignKey("fee_structures.id"), nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending / partially_paid / paid / overdue / exempted


class Payment(Base, TimestampMixin):
    """
    Un paiement. Jamais de suppression physique: seulement une ANNULATION
    tracée dans audit_logs (voir règle du cahier des charges §29-30).
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    method: Mapped[str] = mapped_column(String(30), nullable=False)  # cash/transfer/check/mobile_money/other
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    receipt: Mapped["Receipt | None"] = relationship(back_populates="payment", uselist=False)


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), unique=True, nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # REC-2026-000154
    print_count: Mapped[int] = mapped_column(default=1, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    payment: Mapped["Payment"] = relationship(back_populates="receipt")


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    spent_at: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class CashRegisterClosure(Base, TimestampMixin):
    """Clôture de caisse journalière/périodique."""

    __tablename__ = "cash_register_closures"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    closed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    closure_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_receipts: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
