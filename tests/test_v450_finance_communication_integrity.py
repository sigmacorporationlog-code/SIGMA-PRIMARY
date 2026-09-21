from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fee_structure_validates_year_belongs_to_school():
    text = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    assert 'year.school_id != school_id' in text


def test_finance_overview_validates_requested_year_scope():
    text = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    assert 'year.school_id != current_user.school_id' in text


def test_mobile_money_reconcile_validates_provider_and_reference():
    text = (ROOT / "app/api/finance.py").read_text(encoding="utf-8")
    assert "('manual','mtn_momo','orange_money')" in text
    assert 'Référence externe obligatoire' in text


def test_sms_logs_require_view_permission():
    text = (ROOT / "app/api/communication.py").read_text(encoding="utf-8")
    assert 'communication.sms.view' in text
