from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_finance_sensitive_reads_and_prints_are_permission_gated():
    s = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    assert 'finance.payments.view' in s
    assert 'finance.payments.print_receipt' in s


def test_communication_sms_enforces_tenant_before_dispatch():
    s = (ROOT / "app/api/communication.py").read_text(encoding="utf-8")
    assert 'assert_school_access(current_user, payload.school_id)' in s
    assert 'Student.school_id == payload.school_id' in s
    assert 'year.school_id != payload.school_id' in s


def test_organization_mutations_require_settings_permission():
    s = (ROOT / "app/api/organization.py").read_text(encoding="utf-8")
    for route in ('/campuses', '/academic-years', '/academic-periods'):
        pos = s.index(f'@router.post("{route}"')
        snippet = s[pos:pos+180]
        assert 'administration.settings.modify' in snippet, route


def test_whatsapp_configuration_is_admin_only():
    s = (ROOT / "app/api/communication_v3.py").read_text(encoding="utf-8")
    pos = s.index('@router.post("/whatsapp/config"')
    assert 'administration.settings.modify' in s[pos:pos+180]


def test_dashboard_stats_pdf_is_tenant_bound():
    s = (ROOT / "app/api/dashboard.py").read_text(encoding="utf-8")
    pos = s.index('@router.get("/stats.pdf")')
    assert '_assert_school_access(school_id, current_user)' in s[pos:pos+900]
    assert 'year.school_id != school_id' in s[pos:pos+1400]


def test_onboarding_bootstrap_requires_settings_permission():
    s = (ROOT / "app/api/onboarding.py").read_text(encoding="utf-8")
    pos = s.index("@router.post('/{school_id}/bootstrap'")
    assert 'administration.settings.modify' in s[pos:pos+220]


def test_finance_overviews_and_mobile_money_reconciliation_are_permission_gated():
    s = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    for route, perm in (("/finance/overview", "finance.payments.view"), ("/finance/overdue", "finance.payments.view"), ("/payments/{payment_id}/mobile-money/reconcile", "finance.payments.record")):
        pos = s.index(f'@router.', s.index(route)-40)
        assert perm in s[pos:pos+220], route
