from pathlib import Path

def test_finance_v3_model_and_migration_present():
    assert Path('app/models/finance_v3.py').exists()
    assert Path('alembic/versions/20260914_3300_finance_v3.py').exists()

def test_payment_amount_guard_and_double_count_fix():
    text=Path('app/api/finance.py').read_text(encoding="utf-8")
    assert 'payload.amount > balance' in text
    assert 'total_paid += payload.amount' not in text
    assert 'refresh_invoice_status(db, invoice)' in text
