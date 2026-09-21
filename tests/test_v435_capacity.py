from app.services.capacity import capacity_snapshot
from app.services.observability import record_request


def test_capacity_snapshot_contains_limits_and_pool():
    data = capacity_snapshot()
    assert "limits" in data
    assert "database" in data
    assert "observability" in data
    assert data["limits"]["db_pool_size"] >= 1


def test_capacity_warns_on_slow_requests():
    record_request("GET", "/api/capacity-test", 200, 2500)
    data = capacity_snapshot()
    assert "latence p95 au-dessus du seuil configuré" in data["warnings"]
