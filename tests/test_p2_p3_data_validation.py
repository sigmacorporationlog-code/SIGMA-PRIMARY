from datetime import date
from decimal import Decimal

import pytest


def test_student_phone_normalization_rejects_invalid_number():
    from app.schemas.students import GuardianCreate, StudentCreate

    with pytest.raises(ValueError):
        StudentCreate(school_id=1, first_name="A", last_name="B", guardian_phone="not-a-phone")
    assert GuardianCreate(
        school_id=1,
        first_name="A",
        last_name="B",
        relationship_type="Parent",
        phone="+237 699 123 456",
    ).phone == "+237699123456"


def test_financial_decimal_boundaries_are_exact():
    from app.schemas.finance import InvoiceCreate, PaymentCreate

    with pytest.raises(ValueError):
        InvoiceCreate(
            student_id=1,
            academic_year_id=1,
            fee_structure_id=1,
            amount_due=Decimal("100.005"),
        )

    invoice = InvoiceCreate(
        student_id=1,
        academic_year_id=1,
        fee_structure_id=1,
        amount_due=Decimal("100.00"),
        discount_amount=Decimal("0.01"),
        due_date=date(2026, 9, 20),
    )
    assert invoice.amount_due == Decimal("100.00")
    assert invoice.discount_amount == Decimal("0.01")

    with pytest.raises(ValueError):
        InvoiceCreate(
            student_id=1,
            academic_year_id=1,
            fee_structure_id=1,
            amount_due=Decimal("100.00"),
            discount_amount=Decimal("100.01"),
        )

    with pytest.raises(ValueError):
        PaymentCreate(invoice_id=1, student_id=1, amount=Decimal("12.345"), method="cash")
    assert PaymentCreate(invoice_id=1, student_id=1, amount=Decimal("12.35"), method="cash").amount == Decimal("12.35")


def test_gpa_mode_is_explicit_and_closed_set():
    from app.schemas.evaluation import ConfigPatch, FrameworkCreate

    assert FrameworkCreate(school_id=1, school_year_id=1, section="en", cycle="primary", name="EN", gpa_mode="subject_weighted").gpa_mode == "subject_weighted"
    assert ConfigPatch(gpa_mode="overall_scale").gpa_mode == "overall_scale"
    with pytest.raises(ValueError):
        FrameworkCreate(school_id=1, school_year_id=1, section="en", cycle="primary", name="EN", gpa_mode="custom")
    with pytest.raises(ValueError):
        ConfigPatch(gpa_mode="custom")
