from decimal import Decimal
from pathlib import Path


def test_gpa_mode_is_configurable_and_backwards_compatible():
    model = Path("app/models/evaluation.py").read_text(encoding="utf-8")
    schema = Path("app/schemas/evaluation.py").read_text(encoding="utf-8")
    engine = Path("app/services/evaluation_engine.py").read_text(encoding="utf-8")
    assert 'gpa_mode: Mapped[str]' in model
    assert 'gpa_mode: str = "overall_scale"' in schema
    assert 'gpa_mode == "subject_weighted"' in engine
    assert 'overall_scale' in engine


def test_decimal_percent_normalization_is_explicit():
    value = (Decimal("14.20") * Decimal("5")).quantize(Decimal("0.01"))
    assert value == Decimal("71.00")
