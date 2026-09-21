from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services.billing_v4 import issue_invoice, issue_renewal_invoice, register_payment, register_provider_payment, list_invoices, reconcile_subscriptions

router=APIRouter(prefix='/api/cloud/billing', tags=['SIGMA Billing'])

def _allowed(school_id:int,user:User):
    if not (user.is_superadmin or user.school_id==school_id): raise HTTPException(403,'Accès refusé')

class InvoiceRequest(BaseModel):
    school_id:int=Field(ge=1)
    annual:bool=False
    due_days:int=Field(default=10,ge=0,le=90)

@router.post('/invoices')
def create_invoice(payload:InvoiceRequest, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(403,'Réservé au contrôle central SIGMA')
    try: inv=issue_invoice(db,payload.school_id,payload.annual,payload.due_days)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'id':inv.id,'invoice_number':inv.invoice_number,'school_id':inv.school_id,'amount_xaf':inv.amount_xaf,'due_on':inv.due_on.isoformat(),'status':inv.status}

@router.get('/invoices')
def invoices(school_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    _allowed(school_id,current_user)
    return {'items':[{'id':i.id,'invoice_number':i.invoice_number,'amount_xaf':i.amount_xaf,'due_on':i.due_on.isoformat(),'status':i.status,'paid_at':i.paid_at.isoformat() if i.paid_at else None} for i in list_invoices(db,school_id)]}

class PaymentRequest(BaseModel):
    invoice_id:int=Field(ge=1)
    amount_xaf:int=Field(gt=0)
    method:str=Field(min_length=2,max_length=40)
    provider_reference:str|None=None

@router.post('/payments')
def payment(payload:PaymentRequest,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    from app.models.billing_v4 import SubscriptionInvoice
    inv=db.get(SubscriptionInvoice,payload.invoice_id)
    if not inv: raise HTTPException(404,'Facture introuvable')
    # A manual payment is an accounting mutation: allowing an ordinary
    # school user to mark an invoice as paid would activate a subscription
    # without any verified external settlement. Keep this path in the
    # central control plane; provider callbacks use the idempotent endpoint
    # below and are also centrally authenticated.
    if not current_user.is_superadmin: raise HTTPException(403,'Seul le contrôle central SIGMA peut valider un paiement manuel')
    try: p=register_payment(db,**payload.model_dump(), actor=current_user)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'id':p.id,'invoice_id':p.invoice_id,'amount_xaf':p.amount_xaf,'status':p.status,'paid_at':p.paid_at.isoformat() if p.paid_at else None}


class RenewalRequest(BaseModel):
    school_id:int=Field(ge=1)
    annual:bool=False
    due_days:int=Field(default=10,ge=0,le=90)

@router.post('/renewals')
def renewal(payload:RenewalRequest, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(403,'Réservé au contrôle central SIGMA')
    try: inv=issue_renewal_invoice(db,payload.school_id,payload.annual,payload.due_days)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'id':inv.id,'invoice_number':inv.invoice_number,'school_id':inv.school_id,'period_start':inv.period_start.isoformat(),'period_end':inv.period_end.isoformat(),'amount_xaf':inv.amount_xaf,'due_on':inv.due_on.isoformat(),'status':inv.status}

class ReconcileRequest(BaseModel):
    today:str|None=None

@router.post('/reconcile')
def reconcile(payload:ReconcileRequest, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(403,'Réservé au contrôle central SIGMA')
    from datetime import date
    try: today=date.fromisoformat(payload.today) if payload.today else None
    except ValueError as exc: raise HTTPException(400,'today doit être YYYY-MM-DD') from exc
    return reconcile_subscriptions(db,today)

class ProviderPaymentRequest(BaseModel):
    invoice_id:int=Field(ge=1)
    amount_xaf:int=Field(gt=0)
    method:str=Field(min_length=2,max_length=40)
    provider_reference:str=Field(min_length=2,max_length=150)
    external_event_id:str=Field(min_length=2,max_length=150)

@router.post('/payments/provider')
def provider_payment(payload:ProviderPaymentRequest, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    if not current_user.is_superadmin: raise HTTPException(403,'Réservé au contrôle central SIGMA')
    from app.models.billing_v4 import SubscriptionInvoice
    inv=db.get(SubscriptionInvoice,payload.invoice_id)
    if not inv: raise HTTPException(404,'Facture introuvable')
    try: p=register_provider_payment(db,**payload.model_dump(), actor=current_user)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'id':p.id,'invoice_id':p.invoice_id,'amount_xaf':p.amount_xaf,'status':p.status,'external_event_id':p.external_event_id,'paid_at':p.paid_at.isoformat() if p.paid_at else None}
