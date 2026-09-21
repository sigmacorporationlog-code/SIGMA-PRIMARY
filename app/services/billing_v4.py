from __future__ import annotations
from calendar import monthrange
from datetime import date, timedelta, datetime, timezone
from secrets import token_hex
from sqlalchemy.orm import Session
from app.models.billing_v4 import SubscriptionInvoice, SubscriptionPayment
from app.models.cloud import SchoolSubscription, CloudPlan
from app.models.security import User
from app.services.cloud import log_cloud_event

def _next_period(start: date, annual: bool):
    if annual: return date(start.year + 1, start.month, min(start.day, monthrange(start.year + 1, start.month)[1]))
    y, m = (start.year + 1, 1) if start.month == 12 else (start.year, start.month + 1)
    return date(y, m, min(start.day, monthrange(y, m)[1]))

def issue_invoice(db: Session, school_id: int, annual: bool = False, due_days: int = 10) -> SubscriptionInvoice:
    sub = db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school_id).first()
    if not sub: raise ValueError('Abonnement introuvable')
    plan = db.query(CloudPlan).filter(CloudPlan.code == sub.plan_code, CloudPlan.is_active.is_(True)).first()
    if not plan: raise ValueError('Plan Cloud introuvable')
    start = date.today(); end = _next_period(start, annual) - timedelta(days=1)
    existing = db.query(SubscriptionInvoice).filter(
        SubscriptionInvoice.school_id == school_id,
        SubscriptionInvoice.period_start == start,
        SubscriptionInvoice.period_end == end,
    ).first()
    if existing:
        return existing
    amount = plan.annual_price_xaf if annual else plan.monthly_price_xaf
    number = f'SIGMA-{start.strftime("%Y%m%d")}-{school_id}-{token_hex(6).upper()}'
    inv = SubscriptionInvoice(school_id=school_id, subscription_id=sub.id, invoice_number=number, period_start=start, period_end=end, amount_xaf=amount, due_on=start + timedelta(days=due_days), status='issued')
    db.add(inv); db.commit(); db.refresh(inv); return inv

def register_payment(db: Session, invoice_id: int, amount_xaf: int, method: str, provider_reference: str | None = None, actor: User | None = None) -> SubscriptionPayment:
    inv = db.get(SubscriptionInvoice, invoice_id)
    if not inv: raise ValueError('Facture introuvable')
    sub = db.get(SchoolSubscription, inv.subscription_id)
    if not sub or sub.school_id != inv.school_id:
        raise ValueError('Cohérence facture/abonnement invalide')
    if amount_xaf <= 0: raise ValueError('Montant invalide')
    if inv.status == 'paid': raise ValueError('Facture déjà réglée')
    if inv.status not in {'issued', 'overdue'}: raise ValueError('Facture non payable dans son état actuel')
    if provider_reference:
        duplicate_ref = db.query(SubscriptionPayment).filter(
            SubscriptionPayment.provider_reference == provider_reference,
            SubscriptionPayment.status == 'paid',
        ).first()
        if duplicate_ref and duplicate_ref.invoice_id != invoice_id:
            raise ValueError('Référence fournisseur déjà utilisée pour une autre facture')
    paid = db.query(SubscriptionPayment).filter(SubscriptionPayment.invoice_id == invoice_id, SubscriptionPayment.status == 'paid').all()
    already = sum(p.amount_xaf for p in paid)
    if already + amount_xaf > inv.amount_xaf: raise ValueError('Le paiement dépasse le solde de la facture')
    payment = SubscriptionPayment(school_id=inv.school_id, invoice_id=invoice_id, amount_xaf=amount_xaf, method=method, provider_reference=provider_reference, status='paid', paid_at=datetime.now(timezone.utc))
    db.add(payment)
    total = already + amount_xaf
    if total >= inv.amount_xaf:
        inv.status='paid'; inv.paid_at=datetime.now(timezone.utc)
        if sub:
            sub.status = 'active'
            sub.suspended_on = None
            if not sub.ends_on or sub.ends_on < inv.period_end:
                sub.ends_on = inv.period_end
    db.commit(); db.refresh(payment)
    log_cloud_event(db, inv.school_id, 'billing.payment.recorded', actor, {'invoice_id': inv.id, 'payment_id': payment.id, 'amount_xaf': payment.amount_xaf, 'method': payment.method, 'provider_reference': bool(payment.provider_reference), 'invoice_status': inv.status})
    return payment

def list_invoices(db: Session, school_id: int):
    rows = db.query(SubscriptionInvoice).filter(SubscriptionInvoice.school_id == school_id).order_by(SubscriptionInvoice.id.desc()).all()
    for row in rows:
        if row.status == 'issued' and row.due_on < date.today(): row.status='overdue'
    db.commit(); return rows


def _period_from(start: date, annual: bool):
    end = _next_period(start, annual) - timedelta(days=1)
    return start, end


def issue_renewal_invoice(db: Session, school_id: int, annual: bool = False, due_days: int = 10) -> SubscriptionInvoice:
    """Create the next renewal invoice idempotently, based on the subscription end date."""
    sub = db.query(SchoolSubscription).filter(SchoolSubscription.school_id == school_id).first()
    if not sub:
        raise ValueError('Abonnement introuvable')
    plan = db.query(CloudPlan).filter(CloudPlan.code == sub.plan_code, CloudPlan.is_active.is_(True)).first()
    if not plan:
        raise ValueError('Plan Cloud introuvable')
    start = (sub.ends_on + timedelta(days=1)) if sub.ends_on and sub.ends_on >= date.today() else date.today()
    start, end = _period_from(start, annual)
    existing = db.query(SubscriptionInvoice).filter(
        SubscriptionInvoice.school_id == school_id,
        SubscriptionInvoice.period_start == start,
        SubscriptionInvoice.period_end == end,
    ).first()
    if existing:
        return existing
    amount = plan.annual_price_xaf if annual else plan.monthly_price_xaf
    number = f'SIGMA-{start.strftime("%Y%m%d")}-{school_id}-{token_for_invoice()}'
    inv = SubscriptionInvoice(school_id=school_id, subscription_id=sub.id,
        invoice_number=number, period_start=start, period_end=end,
        amount_xaf=amount, due_on=date.today() + timedelta(days=due_days), status='issued')
    db.add(inv); db.commit(); db.refresh(inv)
    return inv


def token_for_invoice() -> str:
    from secrets import token_hex
    return token_hex(6).upper()


def reconcile_subscriptions(db: Session, today: date | None = None) -> dict:
    """Mark overdue invoices, suspend expired subscriptions after grace, and reactivate paid renewals."""
    today = today or date.today()
    changed = {'overdue_invoices': 0, 'suspended': 0, 'reactivated': 0}
    rows = db.query(SubscriptionInvoice).filter(SubscriptionInvoice.status.in_(['issued', 'overdue', 'paid'])).all()
    for inv in rows:
        if inv.status == 'issued' and inv.due_on < today:
            inv.status = 'overdue'; changed['overdue_invoices'] += 1
    subs = db.query(SchoolSubscription).all()
    for sub in subs:
        paid_renewal = db.query(SubscriptionInvoice).filter(
            SubscriptionInvoice.school_id == sub.school_id,
            SubscriptionInvoice.status == 'paid',
            SubscriptionInvoice.period_end >= today,
        ).order_by(SubscriptionInvoice.period_end.desc()).first()
        if paid_renewal and sub.status == 'suspended':
            sub.status = 'active'; sub.suspended_on = None; sub.ends_on = max(sub.ends_on or today, paid_renewal.period_end); changed['reactivated'] += 1
            log_cloud_event(db, sub.school_id, 'subscription.reactivated', None, {'reason': 'paid_renewal', 'period_end': paid_renewal.period_end.isoformat()})
            continue
        if sub.status in {'active', 'trial'} and sub.ends_on and today > sub.ends_on:
            grace = max(0, sub.grace_period_days or 0)
            if today > sub.ends_on + timedelta(days=grace):
                sub.status = 'suspended'; sub.suspended_on = today; changed['suspended'] += 1
                log_cloud_event(db, sub.school_id, 'subscription.suspended', None, {'reason': 'expired_after_grace', 'ends_on': sub.ends_on.isoformat(), 'grace_period_days': grace})
    db.commit()
    return changed


def register_provider_payment(db: Session, invoice_id: int, amount_xaf: int, method: str,
                               provider_reference: str, external_event_id: str, actor: User | None = None) -> SubscriptionPayment:
    if not external_event_id:
        raise ValueError('external_event_id requis')
    existing = db.query(SubscriptionPayment).filter(SubscriptionPayment.external_event_id == external_event_id).first()
    if existing:
        return existing
    payment = register_payment(db, invoice_id, amount_xaf, method, provider_reference, actor=actor)
    payment.external_event_id = external_event_id
    db.commit(); db.refresh(payment)
    return payment
