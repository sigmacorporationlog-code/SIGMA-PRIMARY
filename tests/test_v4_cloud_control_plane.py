from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v4_control_plane_layer_present():
    model = (ROOT / "app/models/cloud.py").read_text(encoding="utf8")
    service = (ROOT / "app/services/cloud.py").read_text(encoding="utf8")
    api = (ROOT / "app/api/cloud.py").read_text(encoding="utf8")
    assert "class CloudPlan" in model
    assert "class CloudUsageSnapshot" in model
    assert "issue_license_key" in service
    assert "activate_license" in service
    assert '@router.get("/control-plane")' in api
    assert '@router.post("/license/issue")' in api
    assert '@router.post("/license/activate")' in api


def test_v4_migration_exists_and_follows_cloud_commercial():
    migration = (ROOT / "alembic/versions/20260914_4000_cloud_control_plane.py").read_text(encoding="utf8")
    assert 'down_revision = "20260914_3800"' in migration
    assert '"cloud_plans"' in migration
    assert '"cloud_usage_snapshots"' in migration


def test_v4_plan_catalog_contains_commercial_offers():
    service = (ROOT / "app/services/cloud.py").read_text(encoding="utf8")
    assert '"starter"' in service
    assert '"standard"' in service
    assert '"premium"' in service
    assert 'monthly_price_xaf' in service
