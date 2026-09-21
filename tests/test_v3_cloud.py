from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_layer_present():
    assert (ROOT / "app/models/cloud.py").exists()
    assert (ROOT / "app/services/cloud.py").exists()
    api = (ROOT / "app/api/cloud.py").read_text(encoding="utf8")
    assert '@router.get("/overview")' in api
    assert '@router.put("/subscription")' in api
    assert 'audit_integrity' in api


def test_audit_chain_fields_and_service():
    model = (ROOT / "app/models/security.py").read_text(encoding="utf8")
    service = (ROOT / "app/services/audit.py").read_text(encoding="utf8")
    assert "previous_hash" in model and "entry_hash" in model
    assert "audit_chain_digest" in service


def test_multischool_organization_is_hardened():
    api = (ROOT / "app/api/organization.py").read_text(encoding="utf8")
    assert "_assert_school_access" in api
    assert "Seul un superadministrateur peut créer un groupe" in api
    assert "current_user: User = Depends(get_current_user)" in api
