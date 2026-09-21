from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def test_academic_scoring_models_use_numeric_not_float():
    academic = Path("app/models/academic.py").read_text(encoding="utf-8")
    evaluation = Path("app/models/evaluation.py").read_text(encoding="utf-8")
    assert "mapped_column(Float" not in academic
    assert "mapped_column(Float" not in evaluation
    assert "Numeric(10, 4)" in academic
    assert "Numeric(10, 4)" in evaluation


def test_decimal_half_up_boundary_is_explicit():
    value = (Decimal("10.005")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert value == Decimal("10.01")
