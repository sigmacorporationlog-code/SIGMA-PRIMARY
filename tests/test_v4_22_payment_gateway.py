import hashlib
import hmac
import json
from pathlib import Path

from app.core.config import settings
from app.services.payment_gateway import verify_signature

ROOT = Path(__file__).resolve().parents[1]


def test_v422_signed_webhook_verification():
    original = settings.PAYMENT_WEBHOOK_SECRET
    try:
        settings.PAYMENT_WEBHOOK_SECRET = "test-secret"
        raw = b'{"event_id":"evt-1"}'
        signature = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
        assert verify_signature(raw, signature)
        assert verify_signature(raw, "sha256=" + signature)
        assert not verify_signature(raw, signature[:-1] + "0")
    finally:
        settings.PAYMENT_WEBHOOK_SECRET = original


def test_v422_empty_secret_disables_webhook_signature():
    original = settings.PAYMENT_WEBHOOK_SECRET
    try:
        settings.PAYMENT_WEBHOOK_SECRET = ""
        assert not verify_signature(b"{}", "anything")
    finally:
        settings.PAYMENT_WEBHOOK_SECRET = original


def test_v422_payment_gateway_model_and_migration_present():
    model = (ROOT / "app/models/payment_gateway.py").read_text(encoding="utf8")
    migration = (ROOT / "alembic/versions/20260915_5100_payment_gateway.py").read_text(encoding="utf8")
    assert "PaymentGatewayEvent" in model
    assert "uq_payment_gateway_event_provider_external" in migration
    assert "payment_gateway_events" in migration


def test_v422_webhook_api_is_public_but_signature_protected():
    api = (ROOT / "app/api/payment_gateway.py").read_text(encoding="utf8")
    assert '/webhooks/{provider}' in api
    assert 'x_signature' in api
    assert 'process_webhook' in api


def test_v422_billing_uses_external_event_id_for_idempotence():
    billing = (ROOT / "app/services/billing_v4.py").read_text(encoding="utf8")
    gateway = (ROOT / "app/services/payment_gateway.py").read_text(encoding="utf8")
    assert 'external_event_id' in billing
    assert 'provider}:{event_id}' in gateway
    assert 'duplicate' in gateway
