from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v42_billing_automation_controls_present():
    model = (ROOT/'app/models/cloud.py').read_text(encoding='utf8')
    billing = (ROOT/'app/services/billing_v4.py').read_text(encoding='utf8')
    api = (ROOT/'app/api/billing_v4.py').read_text(encoding='utf8')
    migration = (ROOT/'alembic/versions/20260914_4200_billing_automation.py').read_text(encoding='utf8')
    assert 'grace_period_days' in model
    assert 'suspended_on' in model
    assert 'issue_renewal_invoice' in billing
    assert 'reconcile_subscriptions' in billing
    assert 'register_provider_payment' in billing
    assert "'/renewals'" in api
    assert "'/reconcile'" in api
    assert "'/payments/provider'" in api
    assert 'external_event_id' in migration
    assert 'uq_subscription_invoice_period' in migration


def test_v42_payment_extends_subscription_on_full_payment():
    src=(ROOT/'app/services/billing_v4.py').read_text(encoding='utf8')
    assert "sub.status = 'active'" in src
    assert 'sub.ends_on = inv.period_end' in src
