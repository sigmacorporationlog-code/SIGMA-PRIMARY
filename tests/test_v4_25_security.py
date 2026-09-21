import sys
import types

# The isolated CI image used for this audit does not ship runtime auth wheels
# (bcrypt/python-jose). These shims only allow importing endpoint modules;
# authentication integration is validated separately against the declared requirements.
if "bcrypt" not in sys.modules:
    bcrypt_stub = types.ModuleType("bcrypt")
    bcrypt_stub.hashpw = lambda *a, **k: b"stub"
    bcrypt_stub.checkpw = lambda *a, **k: False
    bcrypt_stub.gensalt = lambda *a, **k: b"stub"
    sys.modules["bcrypt"] = bcrypt_stub
if "jose" not in sys.modules:
    jose_stub = types.ModuleType("jose")
    jose_stub.JWTError = type("JWTError", (Exception,), {})
    import jwt as _pyjwt
    def _decode(*args, **kwargs):
        try:
            return _pyjwt.decode(*args, **kwargs)
        except Exception as exc:
            raise jose_stub.JWTError(str(exc)) from exc
    jose_stub.jwt = types.SimpleNamespace(encode=_pyjwt.encode, decode=_decode)
    sys.modules["jose"] = jose_stub

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.database import Base
from app.core.config import settings
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.students import Student, SchoolClass, Level
from app.models.security import User
from app.models.academic import ReportCard
from app.api.students import change_student_status, withdraw_student, list_class_students, create_enrollment
from app.api.academic import get_class_ranking, get_student_average, publish_report_card
from app.api.finance import get_receipt, download_receipt_pdf
from app.services.media import resolve_media_path


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def schools_and_users(db):
    a, b = School(name="A", currency="XAF", language="fr"), School(name="B", currency="XAF", language="fr")
    db.add_all([a, b]); db.flush()
    ua = User(school_id=a.id, username="ua", hashed_password="x", first_name="A", last_name="User")
    ub = User(school_id=b.id, username="ub", hashed_password="x", first_name="B", last_name="User")
    db.add_all([ua, ub]); db.flush()
    return a, b, ua, ub


def test_refresh_rejects_malformed_subject(monkeypatch):
    from app.api.auth import refresh
    from app.core.security import create_refresh_token
    db = setup_db()
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-0123456789012345678901234567890123456789")
    token = create_refresh_token("not-an-integer", 1)
    with pytest.raises(HTTPException) as exc:
        refresh(token, db)
    assert exc.value.status_code == 401


def test_token_version_revokes_access_token(monkeypatch):
    from app.core.security import create_access_token
    from app.deps import get_current_user
    db = setup_db()
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-0123456789012345678901234567890123456789")
    school = School(name="Token School", currency="XAF", language="fr")
    db.add(school); db.flush()
    user = User(school_id=school.id, username="token-user", hashed_password="x", first_name="T", last_name="U")
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(str(user.id), {"school_id": school.id, "token_version": user.token_version})
    assert get_current_user(token, db).id == user.id
    user.token_version += 1; db.commit()
    with pytest.raises(HTTPException) as exc:
        get_current_user(token, db)
    assert exc.value.status_code == 401


def test_cross_tenant_student_mutations_are_denied():
    db = setup_db(); _, b, ua, _ = schools_and_users(db)
    student = Student(school_id=b.id, matricule="B1", first_name="B", last_name="Student")
    db.add(student); db.flush()
    with pytest.raises(HTTPException) as exc:
        change_student_status(student.id, "graduated", db, ua)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        withdraw_student(student.id, db, ua)
    assert exc.value.status_code == 404


def test_cross_tenant_class_listing_is_denied():
    db = setup_db(); _, b, ua, _ = schools_and_users(db)
    year = AcademicYear(school_id=b.id, label="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
    db.add(year); db.flush()
    level = Level(school_id=b.id, name="Primaire", order_index=1)
    db.add(level); db.flush()
    cls = SchoolClass(school_id=b.id, academic_year_id=year.id, level_id=level.id, name="B1")
    db.add(cls); db.commit()
    with pytest.raises(HTTPException) as exc:
        list_class_students(cls.id, db, ua)
    assert exc.value.status_code == 404


def test_enrollment_rejects_cross_tenant_student_or_class():
    db = setup_db(); a, b, ua, _ = schools_and_users(db)
    year_b = AcademicYear(school_id=b.id, label="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
    db.add(year_b); db.flush()
    level_b = Level(school_id=b.id, name="Primaire", order_index=1)
    db.add(level_b); db.flush()
    cls_b = SchoolClass(school_id=b.id, academic_year_id=year_b.id, level_id=level_b.id, name="B1")
    student_b = Student(school_id=b.id, matricule="B1", first_name="B", last_name="Student")
    db.add_all([cls_b, student_b]); db.commit()
    from app.schemas.students import EnrollmentCreate
    payload = EnrollmentCreate(student_id=student_b.id, class_id=cls_b.id, academic_year_id=year_b.id, enrolled_at=date.today(), enrollment_type="mutation")
    with pytest.raises(HTTPException) as exc:
        create_enrollment(payload, db, ua)
    assert exc.value.status_code == 400


def test_cross_tenant_academic_reads_are_denied():
    db = setup_db(); _, b, ua, _ = schools_and_users(db)
    year_b = AcademicYear(school_id=b.id, label="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
    db.add(year_b); db.flush()
    period_b = AcademicPeriod(academic_year_id=year_b.id, name="T1", order_index=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 31))
    level_b = Level(school_id=b.id, name="Primaire", order_index=1)
    db.add(level_b); db.flush()
    cls_b = SchoolClass(school_id=b.id, academic_year_id=year_b.id, level_id=level_b.id, name="B1")
    student_b = Student(school_id=b.id, matricule="B2", first_name="B", last_name="Student")
    db.add_all([period_b, cls_b, student_b]); db.commit()
    with pytest.raises(HTTPException) as exc:
        get_class_ranking(cls_b.id, period_b.id, db, ua)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        get_student_average(student_b.id, cls_b.id, period_b.id, db, ua)
    assert exc.value.status_code == 404


def test_cross_tenant_report_card_publish_is_denied():
    db = setup_db(); _, b, ua, _ = schools_and_users(db)
    year_b = AcademicYear(school_id=b.id, label="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
    db.add(year_b); db.flush()
    period_b = AcademicPeriod(academic_year_id=year_b.id, name="T1", order_index=1, start_date=date(2026, 9, 1), end_date=date(2026, 12, 31))
    level_b = Level(school_id=b.id, name="Primaire", order_index=1)
    db.add(level_b); db.flush()
    cls_b = SchoolClass(school_id=b.id, academic_year_id=year_b.id, level_id=level_b.id, name="B1")
    student_b = Student(school_id=b.id, matricule="B3", first_name="B", last_name="Student")
    db.add_all([period_b, cls_b, student_b]); db.flush()
    rc = ReportCard(student_id=student_b.id, class_id=cls_b.id, academic_period_id=period_b.id, is_published=False)
    db.add(rc); db.commit()
    with pytest.raises(HTTPException) as exc:
        publish_report_card(rc.id, db, ua)
    assert exc.value.status_code == 404
    db.refresh(rc)
    assert rc.is_published is False


def test_cross_tenant_finance_receipt_is_denied():
    from app.models.finance import Invoice, Payment, Receipt, FeeStructure
    db = setup_db(); _, b, ua, ub = schools_and_users(db)
    student_b = Student(school_id=b.id, matricule="B4", first_name="B", last_name="Student")
    year_b = AcademicYear(school_id=b.id, label="2026-2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30))
    db.add_all([student_b, year_b]); db.flush()
    fee = FeeStructure(school_id=b.id, academic_year_id=year_b.id, level_id=None, fee_type="scolarite", label="Test", amount=1000)
    db.add(fee); db.flush()
    inv = Invoice(student_id=student_b.id, academic_year_id=year_b.id, fee_structure_id=fee.id, amount_due=1000, discount_amount=0, status="unpaid")
    db.add(inv); db.flush()
    payment = Payment(invoice_id=inv.id, student_id=student_b.id, received_by_id=ub.id, amount=100, method="cash", paid_at=datetime.now(timezone.utc))
    db.add(payment); db.flush()
    receipt = Receipt(payment_id=payment.id, receipt_number="REC-B-1")
    db.add(receipt); db.commit()
    with pytest.raises(HTTPException) as exc:
        get_receipt(payment.id, db, ua)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        download_receipt_pdf(payment.id, db, ua)
    assert exc.value.status_code == 404


def test_media_path_traversal_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        resolve_media_path("../../outside.txt")
    assert exc.value.status_code == 400
