from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]

def test_v41_models_and_migration_present():
    assert (ROOT/'app/models/billing_v4.py').exists()
    assert (ROOT/'app/models/legal.py').exists()
    migration=(ROOT/'alembic/versions/20260914_4100_billing_legal.py').read_text(encoding='utf8')
    for table in ('subscription_invoices','subscription_payments','legal_documents','legal_acceptances','data_processing_authorizations'):
        assert table in migration

def test_legal_documents_are_versioned_and_hashed():
    src=(ROOT/'app/services/legal.py').read_text(encoding='utf8')
    docs=(ROOT/'app/legal/documents.py').read_text(encoding='utf8')
    assert 'content_hash' in src
    assert 'SIGMA-LICENCE' in docs
    assert 'SIGMA-PRIVACY' in docs
    assert 'SIGMA-AUTHORIZATION' in docs
    assert 'LegalAcceptance' in src

def test_legal_documents_contain_required_contract_sections():
    docs=(ROOT/'app/legal/documents.py').read_text(encoding='utf8')
    for phrase in ('Propriété intellectuelle','Données','Paiement','Résiliation','Droits des personnes','Incidents','Autorité du signataire'):
        assert phrase in docs

def test_billing_service_has_invoice_and_payment_controls():
    src=(ROOT/'app/services/billing_v4.py').read_text(encoding='utf8')
    assert 'issue_invoice' in src
    assert 'register_payment' in src
    assert 'Le paiement dépasse le solde' in src
    assert "status='overdue'" in src

def test_legal_and_billing_routes_registered():
    main=(ROOT/'app/main.py').read_text(encoding='utf8')
    assert 'legal' in main and 'billing_v4' in main
    assert '/api/legal' in (ROOT/'app/api/legal.py').read_text(encoding='utf8')
    assert '/api/cloud/billing' in (ROOT/'app/api/billing_v4.py').read_text(encoding='utf8')
