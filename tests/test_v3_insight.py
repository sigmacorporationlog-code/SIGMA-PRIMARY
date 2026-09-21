from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_insight_engine_and_api_present():
    service = (ROOT / 'app/services/insight_engine.py').read_text(encoding='utf8')
    api = (ROOT / 'app/api/dashboard.py').read_text(encoding='utf8')
    ui = (ROOT / 'static/insight.html').read_text(encoding='utf8')
    assert 'def school_insight' in service
    assert 'risk_distribution' in service
    assert 'collection_rate' in service
    assert 'student_risk' in service
    assert '@router.get("/insight")' in api
    assert '/api/dashboard/insight' in ui
    assert 'À traiter maintenant' in ui


def test_insight_is_explicitly_non_diagnostic():
    service = (ROOT / 'app/services/insight_engine.py').read_text(encoding='utf8')
    assert 'sans valeur de diagnostic' in service
