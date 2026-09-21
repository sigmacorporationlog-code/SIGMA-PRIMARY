from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manual_payment_cannot_be_validated_by_school_user():
    api = (ROOT / 'app/api/billing_v4.py').read_text(encoding='utf-8')
    block = api[api.index("@router.post('/payments')"):api.index("class RenewalRequest")]
    assert 'if not current_user.is_superadmin' in block
    assert 'valider un paiement manuel' in block


def test_subscription_update_is_bound_to_catalogue_plan():
    api = (ROOT / 'app/api/cloud.py').read_text(encoding='utf-8')
    block = api[api.index('@router.put("/subscription")'):api.index('@router.post("/subscription/check")')]
    assert 'plan = get_plan(db, payload.plan_code)' in block
    assert 'payload.max_users > plan.max_users' in block
    assert 'payload.max_students > plan.max_students' in block
    assert 'forbidden' in block
    assert 'validate_subscription_usage(db, school_id, require_active=False)' in block


def test_license_issue_rejects_plan_below_current_usage():
    service = (ROOT / 'app/services/cloud.py').read_text(encoding='utf-8')
    block = service[service.index('def issue_license_key'):service.index('def activate_license')]
    assert 'current_users' in block
    assert 'current_students' in block
    assert 'plan.max_users' in block
    assert 'plan.max_students' in block
    assert 'incompatible avec l\'usage actuel' in block


def test_license_activation_rejects_expired_key():
    service = (ROOT / 'app/services/cloud.py').read_text(encoding='utf-8')
    block = service[service.index('def activate_license'):service.index('def control_plane_overview')]
    assert 'sub.ends_on < date.today()' in block
    assert 'license_expired' in block
