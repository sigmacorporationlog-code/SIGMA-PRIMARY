from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_service_exists():
    service = (ROOT / "app/services/production.py").read_text(encoding="utf8")
    assert "production_health" in service
    assert "security_posture" in service
    assert "backup_check" in service


def test_health_endpoints_and_request_id():
    main = (ROOT / "app/main.py").read_text(encoding="utf8")
    assert '/api/health/live' in main
    assert '/api/health/ready' in main
    assert 'settings.REQUEST_ID_HEADER' in main
    assert 'X-Content-Type-Options' in main


def test_system_production_endpoints():
    api = (ROOT / "app/api/system.py").read_text(encoding="utf8")
    assert '/health' in api
    assert '/security-posture' in api
    assert 'production_health' in api
