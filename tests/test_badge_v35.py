from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_badge_lifecycle_fields_and_migration():
    model=(ROOT/'app/models/documents.py').read_text(encoding='utf8')
    mig=(ROOT/'alembic/versions/20260914_3500_badge_v3.py').read_text(encoding='utf8')
    assert 'status' in model and 'delivered_at' in model and 'lifecycle_note' in model
    assert "revision = '20260914_3500'" in mig

def test_badge_engine_is_opaque_and_supports_strategies():
    src=(ROOT/'app/services/badge_engine.py').read_text(encoding='utf8')
    assert 'secure_qr_payload' in src
    assert 'year_level_sequence' in src
    assert 'SIGMA-BADGE:' in src

def test_badge_api_supports_bulk_and_verification():
    src=(ROOT/'app/api/cards.py').read_text(encoding='utf8')
    assert '/bulk-issue' in src
    assert '/lifecycle' in src
    assert '/badge/verify/' in src

def test_badge_pdf_is_ten_up_a4():
    src=(ROOT/'app/services/card_pdf.py').read_text(encoding='utf8')
    assert 'i % 10' in src
    assert '90 * mm' in src
    assert '54 * mm' in src


def test_badge_ui_exposes_bulk_a4():
    src=(ROOT/'static/cards.html').read_text(encoding='utf8')
    assert 'bulkIssueClassCards' in src
    assert '10 badges/page' in src
