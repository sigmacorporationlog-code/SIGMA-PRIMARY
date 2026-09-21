from app.services.observability import record_request, snapshot


def test_observability_records_and_summarizes_requests():
    record_request("GET", "/api/test", 200, 10)
    record_request("GET", "/api/test", 503, 100)
    data = snapshot()
    assert data["total_requests"] >= 2
    assert data["total_5xx"] >= 1
    assert data["latency_ms"]["p95"] >= 10
    assert any(x["route"] == "GET /api/test" for x in data["slowest_routes"])
