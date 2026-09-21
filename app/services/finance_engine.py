from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.finance import Invoice, Payment

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _q(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(value).quantize(CENT)


def paid_amount(db: Session, invoice_id: int) -> Decimal:
    value = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.invoice_id == invoice_id, Payment.is_cancelled.is_(False))
        .scalar()
    )
    return _q(value)



def paid_amounts(db: Session, invoice_ids: list[int]) -> dict[int, Decimal]:
    """Agrège les paiements par facture en une seule requête SQL."""
    if not invoice_ids:
        return {}
    rows = (db.query(Payment.invoice_id, func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.invoice_id.in_(invoice_ids), Payment.is_cancelled.is_(False))
            .group_by(Payment.invoice_id).all())
    return {invoice_id: _q(total) for invoice_id, total in rows}


def balance_map(db: Session, invoices: list[Invoice]) -> dict[int, Decimal]:
    """Calcule les soldes de plusieurs factures sans N+1 SQL."""
    paid = paid_amounts(db, [invoice.id for invoice in invoices])
    return {
        invoice.id: max(ZERO, _q(invoice.amount_due) - _q(invoice.discount_amount) - paid.get(invoice.id, ZERO))
        for invoice in invoices
    }


def refresh_invoice_statuses(db: Session, invoices: list[Invoice]) -> dict[int, str]:
    """Met à jour les statuts d'un lot de factures avec une seule agrégation."""
    paid = paid_amounts(db, [invoice.id for invoice in invoices])
    statuses: dict[int, str] = {}
    today = date.today()
    for invoice in invoices:
        if invoice.status == "exempted":
            statuses[invoice.id] = invoice.status
            continue
        amount_paid = paid.get(invoice.id, ZERO)
        net = max(ZERO, _q(invoice.amount_due) - _q(invoice.discount_amount))
        if amount_paid >= net:
            invoice.status = "paid"
        elif amount_paid > ZERO:
            invoice.status = "partially_paid"
        elif invoice.due_date and invoice.due_date < today:
            invoice.status = "overdue"
        else:
            invoice.status = "pending"
        statuses[invoice.id] = invoice.status
    return statuses


def refresh_invoice_status(db: Session, invoice: Invoice) -> str:
    if invoice.status == "exempted":
        return invoice.status
    paid = paid_amount(db, invoice.id)
    net = max(ZERO, _q(invoice.amount_due) - _q(invoice.discount_amount))
    if paid >= net:
        invoice.status = "paid"
    elif paid > ZERO:
        invoice.status = "partially_paid"
    elif invoice.due_date and invoice.due_date < date.today():
        invoice.status = "overdue"
    else:
        invoice.status = "pending"
    return invoice.status


def invoice_balance(db: Session, invoice: Invoice) -> Decimal:
    paid = paid_amount(db, invoice.id)
    return max(ZERO, _q(invoice.amount_due) - _q(invoice.discount_amount) - paid)
