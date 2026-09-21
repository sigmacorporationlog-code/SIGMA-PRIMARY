from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.config import settings
from app.deps import get_current_user, require_permission, assert_school_access
from app.models.security import User
from app.models.finance import FeeStructure, Invoice, Payment, Receipt
from app.models.finance_v3 import MobileMoneyConfiguration, PaymentTransaction, FinanceReminder
from app.models.students import Student
from app.schemas.finance import (
    FeeStructureCreate, InvoiceCreate, InvoiceOut, PaymentCreate, PaymentOut, ReceiptOut, PaymentCancel,
)
from app.services.audit import log_action
from app.services.pdf_engine import generate_receipt_pdf
from app.services.document_verification import create_document_token
from app.services.finance_engine import refresh_invoice_status, invoice_balance, balance_map, refresh_invoice_statuses
from app.services.cloud import enforce_subscription_feature, SubscriptionError

router = APIRouter(prefix="/api", tags=["Finance"])

def _student_access(db, current_user, student_id):
    student = db.get(Student, student_id)
    if student is None or (student.school_id != current_user.school_id and not current_user.is_superadmin):
        raise HTTPException(status_code=404, detail="Élève introuvable")
    return student

def _invoice_access(db, current_user, invoice_id):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None: raise HTTPException(status_code=404, detail="Facture introuvable")
    student = _student_access(db, current_user, invoice.student_id)
    return invoice, student

def _payment_access(db, current_user, payment_id):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    _student_access(db, current_user, payment.student_id)
    return payment


# ---------- Grille de frais ----------

@router.post("/fee-structures", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_fee_structure(payload: FeeStructureCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, payload.school_id)
    fee = FeeStructure(**payload.model_dump())
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return {"id": fee.id, "label": fee.label, "amount": fee.amount}


@router.get("/fee-structures")
def list_fee_structures(school_id: int, academic_year_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, school_id)
    from app.models.organization import AcademicYear
    year = db.get(AcademicYear, academic_year_id)
    if year is None or year.school_id != school_id:
        raise HTTPException(status_code=400, detail="Année scolaire invalide pour cet établissement")
    fees = db.query(FeeStructure).filter(
        FeeStructure.school_id == school_id, FeeStructure.academic_year_id == academic_year_id
    ).all()
    return [{"id": f.id, "label": f.label, "fee_type": f.fee_type, "amount": f.amount, "level_id": f.level_id} for f in fees]


# ---------- Factures ----------

@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("finance.payments.record"))])
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = _student_access(db, current_user, payload.student_id)
    if payload.academic_year_id is not None:
        from app.models.organization import AcademicYear
        year = db.get(AcademicYear, payload.academic_year_id)
        if year is None or year.school_id != student.school_id:
            raise HTTPException(status_code=400, detail="Année scolaire invalide pour cet établissement")
    invoice = Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/students/{student_id}/invoices", response_model=list[InvoiceOut],
           dependencies=[Depends(require_permission("finance.payments.view"))])
def list_student_invoices(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _student_access(db, current_user, student_id)
    return db.query(Invoice).filter(Invoice.student_id == student_id).all()


@router.get("/students/{student_id}/payments",
           dependencies=[Depends(require_permission("finance.payments.view"))])
def list_student_payments(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Historique des paiements d'un élève, avec le numéro de reçu associé —
    alimente l'écran finance de l'interface."""
    _student_access(db, current_user, student_id)
    payments = db.query(Payment).filter(Payment.student_id == student_id).order_by(Payment.paid_at.desc()).all()
    payment_ids = [p.id for p in payments]
    receipts = ({r.payment_id: r for r in db.query(Receipt).filter(Receipt.payment_id.in_(payment_ids)).all()}
                if payment_ids else {})
    result = []
    for p in payments:
        receipt = receipts.get(p.id)
        result.append({
            "id": p.id, "invoice_id": p.invoice_id, "amount": p.amount, "method": p.method,
            "paid_at": p.paid_at, "is_cancelled": p.is_cancelled, "cancelled_reason": p.cancelled_reason,
            "receipt_number": receipt.receipt_number if receipt else None,
        })
    return result


# ---------- Paiements & reçus ----------

def _generate_receipt_number(db: Session, payment_id: int) -> str:
    # payment_id est déjà alloué par la DB après flush: contrairement à count()+1,
    # il ne peut pas être identique pour deux transactions concurrentes.
    year = datetime.now().year
    return f"REC-{year}-{payment_id:08d}"


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("finance.payments.record"))])
def record_payment(payload: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Contrôle d'accès avant toute réponse basée sur une clé d'idempotence :
    # une clé connue ne doit jamais permettre d'observer un paiement d'un autre établissement.
    _student_access(db, current_user, payload.student_id)
    if payload.idempotency_key:
        existing = db.query(Payment).filter(Payment.idempotency_key == payload.idempotency_key).first()
        if existing is not None:
            if (existing.invoice_id != payload.invoice_id or existing.student_id != payload.student_id
                    or existing.amount != payload.amount or existing.method != payload.method):
                raise HTTPException(status_code=409, detail="Clé d’idempotence déjà utilisée pour une autre opération")
            return existing

    # Sur PostgreSQL, FOR UPDATE sérialise les paiements concurrents sur une même
    # facture. Sur SQLite, le moteur est configuré en BEGIN IMMEDIATE afin que
    # les écritures monétaires concurrentes soient également sérialisées.
    invoice = (db.query(Invoice)
               .filter(Invoice.id == payload.invoice_id)
               .with_for_update()
               .one_or_none())
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    _student_access(db, current_user, invoice.student_id)
    if payload.student_id != invoice.student_id:
        raise HTTPException(status_code=400, detail="L’élève ne correspond pas à la facture")
    balance = invoice_balance(db, invoice)
    if payload.amount > balance:
        raise HTTPException(status_code=400, detail=f"Montant invalide. Solde restant: {balance:.2f}")

    payment = Payment(
        invoice_id=payload.invoice_id,
        student_id=payload.student_id,
        received_by_id=current_user.id,
        amount=payload.amount,
        idempotency_key=payload.idempotency_key,
        method=payload.method,
        paid_at=payload.paid_at or datetime.now(timezone.utc),
    )
    db.add(payment)
    try:
        db.flush()
        receipt = Receipt(payment_id=payment.id, receipt_number=_generate_receipt_number(db, payment.id))
        db.add(receipt)
        refresh_invoice_status(db, invoice)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if payload.idempotency_key:
            existing = db.query(Payment).filter(Payment.idempotency_key == payload.idempotency_key).first()
            if existing is not None:
                return existing
        raise HTTPException(status_code=409, detail="Paiement concurrent ou clé d’idempotence déjà utilisée") from exc

    db.refresh(payment)
    log_action(db, current_user.school_id, current_user, "payment.create", "Payment", payment.id,
               new_value=f"{payload.amount} via {payload.method} (reçu {receipt.receipt_number})")
    return payment


@router.get("/payments/{payment_id}/receipt", response_model=ReceiptOut,
           dependencies=[Depends(require_permission("finance.payments.view"))])
def get_receipt(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _payment_access(db, current_user, payment_id)
    receipt = db.query(Receipt).filter(Receipt.payment_id == payment_id).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    return receipt


@router.post("/payments/{payment_id}/receipt/reprint", response_model=ReceiptOut,
           dependencies=[Depends(require_permission("finance.payments.print_receipt"))])
def reprint_receipt(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Une réimpression doit rester identifiable (compteur incrémenté + audit)."""
    _payment_access(db, current_user, payment_id)
    receipt = db.query(Receipt).filter(Receipt.payment_id == payment_id).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Reçu introuvable")
    receipt.print_count += 1
    db.commit()
    db.refresh(receipt)
    log_action(db, current_user.school_id, current_user, "receipt.reprint", "Receipt", receipt.id,
               new_value=f"impression n°{receipt.print_count}")
    return receipt


@router.get("/payments/{payment_id}/receipt/pdf",
           dependencies=[Depends(require_permission("finance.payments.print_receipt"))])
def download_receipt_pdf(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Reçu de paiement en PDF, prêt à imprimer ou archiver (§29 du cahier
    des charges)."""
    from app.models.organization import School

    payment = _payment_access(db, current_user, payment_id)
    receipt = db.query(Receipt).filter(Receipt.payment_id == payment_id).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Reçu introuvable")

    student = db.get(Student, payment.student_id)
    school = db.get(School, student.school_id) if student else None
    received_by = db.get(User, payment.received_by_id)

    content = generate_receipt_pdf(
        school_name=school.name if school else "SIGMA",
        receipt_number=receipt.receipt_number,
        student_name=f"{student.first_name} {student.last_name}" if student else "—",
        student_matricule=student.matricule if student else "—",
        amount=payment.amount,
        currency=school.currency if school else "XAF",
        method=payment.method,
        paid_at=payment.paid_at.strftime("%d/%m/%Y %H:%M"),
        received_by_name=f"{received_by.first_name} {received_by.last_name}" if received_by else "—",
        print_count=receipt.print_count,
        verification_url=f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/public/documents/verify/{create_document_token('receipt', receipt.id, student.school_id)}",
    )
    # inline (pas attachment) : le reçu s'ouvre directement dans le lecteur
    # PDF du navigateur, qui a son propre bouton Imprimer relié au vrai
    # dialogue d'impression Windows (toutes les imprimantes installées,
    # A4/A3, etc.) — sans étape de téléchargement intermédiaire, ce qui
    # compte pour une caissière qui imprime un reçu à chaque paiement.
    return Response(content=content, media_type="application/pdf",
                     headers={"Content-Disposition": f'inline; filename="recu_{receipt.receipt_number}.pdf"'})


@router.post("/payments/{payment_id}/cancel", dependencies=[Depends(require_permission("finance.payments.cancel"))])
def cancel_payment(payment_id: int, payload: PaymentCancel, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Aucune suppression physique d'un paiement (règle §29-30 du cahier des
    charges): on annule et on trace, la ligne reste consultable.
    """
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Paiement introuvable")
    if payment.is_cancelled:
        raise HTTPException(status_code=400, detail="Ce paiement est déjà annulé")
    _student_access(db, current_user, payment.student_id)

    payment.is_cancelled = True
    payment.cancelled_reason = payload.reason
    invoice = db.get(Invoice, payment.invoice_id)
    if invoice: refresh_invoice_status(db, invoice)
    db.commit()

    log_action(db, current_user.school_id, current_user, "payment.cancel", "Payment", payment.id,
               old_value=f"{payment.amount}", new_value=f"annulé: {payload.reason}")
    return {"status": "ok"}


@router.get("/finance/overview", dependencies=[Depends(require_permission("finance.payments.view"))])
def finance_overview(academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Invoice).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == current_user.school_id)
    if academic_year_id:
        from app.models.organization import AcademicYear
        year = db.get(AcademicYear, academic_year_id)
        if year is None or year.school_id != current_user.school_id:
            raise HTTPException(status_code=400, detail="Année scolaire invalide pour cet établissement")
        q = q.filter(Invoice.academic_year_id == academic_year_id)
    invoices = q.all()
    refresh_invoice_statuses(db, invoices)
    db.commit()
    balances = balance_map(db, invoices)
    total_due = sum((max(0, i.amount_due - i.discount_amount) for i in invoices), 0)
    total_outstanding = sum(balances.values(), 0)
    return {"invoice_count": len(invoices), "total_due": round(total_due,2), "total_outstanding": round(total_outstanding,2), "paid_count": sum(i.status == 'paid' for i in invoices), "overdue_count": sum(i.status == 'overdue' for i in invoices), "partial_count": sum(i.status == 'partially_paid' for i in invoices)}

@router.get("/finance/overdue", dependencies=[Depends(require_permission("finance.payments.view"))])
def overdue_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoices = db.query(Invoice).join(Student, Student.id == Invoice.student_id).filter(Student.school_id == current_user.school_id).all()
    refresh_invoice_statuses(db, invoices)
    balances = balance_map(db, invoices)
    overdue_ids = [inv.student_id for inv in invoices if inv.status == 'overdue']
    students = {s.id:s for s in db.query(Student).filter(Student.id.in_(overdue_ids)).all()} if overdue_ids else {}
    out=[]
    for inv in invoices:
        if inv.status == 'overdue':
            student=students.get(inv.student_id)
            if student:
                out.append({"invoice_id":inv.id,"student_id":inv.student_id,"student_name":f"{student.first_name} {student.last_name}","due_date":inv.due_date,"balance":balances.get(inv.id, 0)})
    db.commit(); return out

@router.post("/finance/mobile-money/config", dependencies=[Depends(require_permission("administration.settings.modify"))])
def save_mobile_money_config(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        enforce_subscription_feature(db, current_user.school_id, "mobile_money")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    provider=payload.get('provider')
    if provider not in ('mtn_momo','orange_money'): raise HTTPException(400,'Fournisseur Mobile Money invalide')
    cfg=MobileMoneyConfiguration(school_id=current_user.school_id, provider=provider, merchant_name=payload.get('merchant_name'), merchant_code=payload.get('merchant_code'), api_base_url=payload.get('api_base_url'), credentials_ref=payload.get('credentials_ref'), is_active=bool(payload.get('is_active',False)))
    db.add(cfg); db.commit(); db.refresh(cfg); return {"id":cfg.id,"provider":cfg.provider,"is_active":cfg.is_active}

@router.post("/invoices/{invoice_id}/reminders", dependencies=[Depends(require_permission("finance.payments.record"))])
def queue_finance_reminder(invoice_id:int, payload:dict, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    invoice, student=_invoice_access(db,current_user,invoice_id)
    channel=payload.get('channel','portal')
    if channel not in ('portal','push','whatsapp','sms'): raise HTTPException(400,'Canal invalide')
    balance=invoice_balance(db,invoice)
    if balance <= 0: raise HTTPException(400,'Cette facture est soldée')
    r=FinanceReminder(school_id=current_user.school_id,invoice_id=invoice_id,channel=channel,recipient=payload.get('recipient'),message=payload.get('message') or f"Rappel de paiement pour {student.first_name} {student.last_name}. Solde: {balance:.0f} XAF")
    db.add(r); db.commit(); db.refresh(r); return {"id":r.id,"status":r.status,"balance":balance}

@router.post("/payments/{payment_id}/mobile-money/reconcile", dependencies=[Depends(require_permission("finance.payments.record"))])
def reconcile_mobile_money(payment_id:int, payload:dict, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    try:
        enforce_subscription_feature(db, current_user.school_id, "mobile_money")
    except SubscriptionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    payment=db.get(Payment,payment_id)
    if not payment: raise HTTPException(404,'Paiement introuvable')
    _student_access(db,current_user,payment.student_id)
    provider=payload.get('provider','manual')
    if provider not in ('manual','mtn_momo','orange_money'):
        raise HTTPException(400,'Fournisseur Mobile Money invalide')
    external_reference=payload.get('external_reference')
    if provider != 'manual' and not external_reference:
        raise HTTPException(400,'Référence externe obligatoire pour un rapprochement Mobile Money')
    tx=PaymentTransaction(school_id=current_user.school_id,payment_id=payment.id,invoice_id=payment.invoice_id,provider=provider,external_reference=external_reference,payer_phone=payload.get('payer_phone'),amount=payment.amount,status='reconciled',provider_message=payload.get('provider_message'))
    db.add(tx); db.commit(); db.refresh(tx); return {"id":tx.id,"status":tx.status,"external_reference":tx.external_reference}
