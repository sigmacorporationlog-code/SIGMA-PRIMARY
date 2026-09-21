import logging
from app.services.observability import normalize_request_id, get_request_id, install_logging_context, set_request_id, reset_request_id, record_request, snapshot


def test_request_id_is_safe_and_bounded():
    value = normalize_request_id("../bad\nvalue")
    assert 8 <= len(value) <= 64
    assert normalize_request_id("A-12345678").startswith("A-")


def test_request_id_context_and_logs_are_correlated():
    token = set_request_id("REQ-12345678")
    try:
        assert get_request_id() == "REQ-12345678"
        record_request("GET", "/api/test", 200, 4.2, request_id=get_request_id())
        install_logging_context()
        record = logging.LogRecord("x", logging.INFO, "x", 1, "message", (), None)
        for filt in logging.getLogger().filters:
            filt.filter(record)
        assert record.request_id == "REQ-12345678"
    finally:
        reset_request_id(token)


def test_observability_does_not_expose_request_id_in_snapshot():
    snap = snapshot()
    text = str(snap)
    assert "REQ-12345678" not in text
    assert "duration_ms" in text or "latency_ms" in text
