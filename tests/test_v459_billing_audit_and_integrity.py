from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_invoice_uses_only_active_catalogue_plan():
    src = (ROOT / 'app/services/billing_v4.py').read_text(encoding='utf8')
    block = src[src.index('def issue_invoice'):src.index('def register_payment')]
    assert "CloudPlan.code == sub.plan_code, CloudPlan.is_active.is_(True)" in block


def test_payment_validates_invoice_subscription_school_coherence():
    src = (ROOT / 'app/services/billing_v4.py').read_text(encoding='utf8')
    block = src[src.index('def register_payment'):src.index('def list_invoices')]
    assert "sub.school_id != inv.school_id" in block
    assert "Cohérence facture/abonnement invalide" in block


def test_billing_mutations_are_audited():
    src = (ROOT / 'app/services/billing_v4.py').read_text(encoding='utf8')
    assert "billing.payment.recorded" in src
    api = (ROOT / 'app/api/billing_v4.py').read_text(encoding='utf8')
    assert 'actor=current_user' in api


def test_provider_payment_preserves_idempotence_and_actor_audit_path():
    src = (ROOT / 'app/services/billing_v4.py').read_text(encoding='utf8')
    block = src[src.index('def register_provider_payment'):]
    assert 'external_event_id' in block
    assert 'actor: User | None = None' in block
    assert 'actor=actor' in block
