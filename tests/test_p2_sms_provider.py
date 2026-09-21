import pytest


def test_fake_provider_is_explicit_simulation(monkeypatch):
    from app.core.config import settings
    from app.services.sms_gateway import FakeDriver, ensure_provider_allowed
    monkeypatch.setattr(settings, "ENV", "pilot")
    driver = FakeDriver()
    assert driver.is_simulation is True
    assert driver.name == "fake"
    ensure_provider_allowed(driver)


def test_production_fake_provider_is_blocked(monkeypatch):
    from app.core.config import settings
    from app.services.sms_gateway import FakeDriver, ensure_provider_allowed
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "SMS_ALLOW_SIMULATION_IN_PRODUCTION", False)
    with pytest.raises(RuntimeError, match="SIMULATION"):
        ensure_provider_allowed(FakeDriver())


def test_invalid_provider_mode_is_rejected(monkeypatch):
    from app.core.config import settings
    from app.services.sms_gateway import get_driver
    monkeypatch.setattr(settings, "SMS_GATEWAY_MODE", "bogus")
    with pytest.raises(RuntimeError):
        get_driver()
