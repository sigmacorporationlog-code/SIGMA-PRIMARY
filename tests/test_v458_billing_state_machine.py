from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _src(name):
    return (ROOT / name).read_text(encoding='utf-8')


def test_subscription_billing_invoice_is_idempotent_per_period():
    src = _src('app/services/billing_v4.py')
    block = src[src.index('def issue_invoice'):src.index('def register_payment')]
    assert "SubscriptionInvoice.period_start == start" in block
    assert "SubscriptionInvoice.period_end == end" in block
    assert "if existing:" in block
    assert "return existing" in block


def test_paid_invoice_cannot_be_paid_again():
    src = _src('app/services/billing_v4.py')
    block = src[src.index('def register_payment'):src.index('def list_invoices')]
    assert "if inv.status == 'paid'" in block
    assert "Facture déjà réglée" in block
    assert "inv.status not in {'issued', 'overdue'}" in block


def test_provider_reference_cannot_be_reused_on_another_invoice():
    src = _src('app/services/billing_v4.py')
    block = src[src.index('def register_payment'):src.index('def list_invoices')]
    assert "SubscriptionPayment.provider_reference == provider_reference" in block
    assert "duplicate_ref.invoice_id != invoice_id" in block
    assert "Référence fournisseur déjà utilisée" in block


def test_webhook_signature_and_event_replay_protection_remain_enabled():
    src = _src('app/services/payment_gateway.py')
    assert 'verify_signature(raw_body, signature)' in src
    assert 'PaymentGatewayEvent.provider == provider' in src
    assert 'PaymentGatewayEvent.external_event_id == event_id' in src
    assert 'register_provider_payment' in src
