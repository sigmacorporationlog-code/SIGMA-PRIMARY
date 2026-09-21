from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_license_issue_never_falls_back_to_inactive_plan():
    src = (ROOT / 'app/services/cloud.py').read_text(encoding='utf-8')
    block = src[src.index('def issue_license_key'):src.index('def activate_license')]
    assert 'plan = get_plan(db, plan_code)' in block
    assert 'ensure_default_plans(db)' in block
    assert 'plan = get_plan(db, plan_code)' in block
    assert 'Plan Cloud inconnu ou inactif' in block
    assert 'next((p for p in ensure_default_plans(db) if p.code == plan_code), None)' not in block


def test_subscription_admin_payload_has_lifecycle_invariants():
    src = (ROOT / 'app/api/cloud.py').read_text(encoding='utf-8')
    block = src[src.index('class SubscriptionUpdate'):src.index('@router.get("/overview")')]
    assert 'model_validator' in src
    assert 'ends_on < self.starts_on' in block
    assert 'status in {"trial", "active"}' in block
    assert 'status == "active" and self.starts_on > date.today()' in block


def test_reconciliation_audits_suspension_and_reactivation():
    src = (ROOT / 'app/services/billing_v4.py').read_text(encoding='utf-8')
    block = src[src.index('def reconcile_subscriptions'):src.index('def register_provider_payment')]
    assert 'subscription.reactivated' in block
    assert 'subscription.suspended' in block
    assert "reason': 'paid_renewal'" in block
    assert "reason': 'expired_after_grace'" in block
