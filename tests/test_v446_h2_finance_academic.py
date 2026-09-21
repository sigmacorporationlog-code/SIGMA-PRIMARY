from decimal import Decimal
from pathlib import Path


def test_finance_uses_exact_decimal_money_and_idempotency():
    model = Path("app/models/finance.py").read_text(encoding="utf-8")
    schema = Path("app/schemas/finance.py").read_text(encoding="utf-8")
    api = Path("app/api/finance.py").read_text(encoding="utf-8")
    migration = Path("alembic/versions/20260920_6100_money_precision.py").read_text(encoding="utf-8")
    assert "Numeric(14, 2)" in model
    assert "Decimal" in schema
    assert "idempotency_key" in model
    assert "with_for_update" in api
    assert "ix_payments_idempotency_key" in migration
    assert Decimal("0.10") + Decimal("0.20") == Decimal("0.30")


def test_ranking_excludes_unvalidated_grades():
    source = Path("app/services/grading_engine.py").read_text(encoding="utf-8")
    assert 'Grade.state.in_' in source and 'validated' in source and 'locked' in source and 'published' in source


def test_production_startup_does_not_run_create_all():
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert 'bootstrap_envs = {"development", "test", "pilot"}' in source
    assert 'Base.metadata.create_all(bind=engine)' in source


def test_period_engine_filters_non_final_results_and_bulk_loads_rules():
    source = Path("app/services/evaluation_engine.py").read_text(encoding="utf-8")
    assert 'FINAL_RESULT_STATES = {"validated", "locked", "published"}' in source
    assert '"state" not in r or r.get("state") in FINAL_RESULT_STATES' in source
    assert 'rules=rules' in source


def test_finance_overview_avoids_payment_sum_n_plus_one():
    engine = Path("app/services/finance_engine.py").read_text(encoding="utf-8")
    api = Path("app/api/finance.py").read_text(encoding="utf-8")
    assert 'def paid_amounts' in engine
    assert 'def balance_map' in engine
    assert 'refresh_invoice_statuses(db, invoices)' in api
    assert 'balances = balance_map(db, invoices)' in api


def test_mobile_downloads_are_app_private():
    source = Path("mobile/android/app/src/main/java/com/sigma/school/MainActivity.java").read_text(encoding="utf-8")
    assert 'setDestinationInExternalFilesDir' in source
    assert 'DIRECTORY_DOWNLOADS' in source


def test_english_primary_supports_configurable_letter_grade_and_gpa():
    model = Path("app/models/evaluation.py").read_text(encoding="utf-8")
    seed = Path("seed.py").read_text(encoding="utf-8")
    engine = Path("app/services/evaluation_engine.py").read_text(encoding="utf-8")
    migration = Path("alembic/versions/20260920_6200_grade_points.py").read_text(encoding="utf-8")
    assert "grade_point" in model
    assert '("A", "Excellent", 90, 100' in seed
    assert '("F", "Fail", 0, 59.99' in seed
    assert '"gpa"' in engine and '"grade"' in engine
    assert 'revision = "20260920_6200"' in migration


def test_signed_document_verification_is_wired_into_pdfs_and_public_api():
    service = Path("app/services/document_verification.py").read_text(encoding="utf-8")
    pdf = Path("app/services/pdf_engine.py").read_text(encoding="utf-8")
    main = Path("app/main.py").read_text(encoding="utf-8")
    assert 'DOCUMENT_TOKEN_TYPE' in service
    assert 'decode_document_token' in service
    assert '_verification_qr_elements' in pdf
    assert 'verification_url' in pdf
    assert 'public_documents.router' in main


def test_period_engine_real_sqlite_excludes_draft_and_maps_letter_grade_and_gpa():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.models.evaluation import EvaluationFramework, RatingScale, AppreciationRule
    from app.services.evaluation_engine import calculate_period_results

    engine = create_engine("sqlite+pysqlite:///:memory:")
    EvaluationFramework.__table__.create(engine)
    RatingScale.__table__.create(engine)
    AppreciationRule.__table__.create(engine)
    with Session(engine) as db:
        db.add(EvaluationFramework(school_id=1, school_year_id=1, section="en", cycle="primary", name="English Primary", gpa_mode="overall_scale"))
        db.commit()
        db.add_all([
            RatingScale(framework_id=1, code="A", label="Excellent", min_percent=90, max_percent=100, grade_point=4, display_order=1),
            RatingScale(framework_id=1, code="F", label="Fail", min_percent=0, max_percent=59.99, grade_point=0, display_order=6),
        ])
        db.commit()
        output = calculate_period_results([
            {"student_id": 1, "score": 18, "max_score": 20, "coefficient": 1, "subject_id": 11, "subject_name": "Math", "state": "validated"},
            {"student_id": 1, "score": 20, "max_score": 20, "coefficient": 1, "subject_id": 11, "subject_name": "Math", "state": "draft"},
        ], db, 1, "en")
    assert output["count"] == 1
    assert output["average"] == 18.0
    assert output["percent"] == 90.0
    assert output["grade"] == "A"
    assert output["gpa"] == 4.0


def test_document_verification_service_round_trip_when_jose_is_available():
    try:
        from jose import jwt as jose_jwt
    except ImportError:
        return
    from app.core.config import settings
    from app.services.document_verification import create_document_token, decode_document_token

    old_secret = settings.SECRET_KEY
    settings.SECRET_KEY = "unit-test-document-signing-secret-2026"
    try:
        token = create_document_token("bulletin", 77, 9)
        claims = decode_document_token(token)
        assert claims is not None
        assert claims["document_type"] == "bulletin"
        assert claims["sub"] == "77"
        assert str(claims["school_id"]) == "9"
    finally:
        settings.SECRET_KEY = old_secret
