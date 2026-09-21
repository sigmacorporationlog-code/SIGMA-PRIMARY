from app.services.pedagogy_engine import _clamp, student_risk


def test_pedagogy_clamp():
    assert _clamp(-10) == 0
    assert _clamp(50.4) == 50
    assert _clamp(140) == 100
