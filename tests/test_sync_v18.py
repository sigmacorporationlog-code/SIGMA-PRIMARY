from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import decide_apply, validate_operation_type


def test_v18_apply_advances_entity_version():
    decision = decide_apply(0, 0)
    assert decision.status == "applied"
    assert decision.new_version == 1
    assert decision.error is None


def test_v18_apply_rejects_stale_operation():
    decision = decide_apply(0, 1)
    assert decision.status == "conflict"
    assert decision.new_version == 1
    assert "Conflit de version" in decision.error


def test_v18_operation_type_validation():
    assert validate_operation_type("update") == "update"
    try:
        validate_operation_type("publish")
    except ValueError as exc:
        assert "invalide" in str(exc)
    else:
        raise AssertionError("Un type d'opération arbitraire doit être refusé")


def test_v18_router_hardening_is_present():
    api = (ROOT / "app/api/sync.py").read_text(encoding="utf8")
    assert '"/apply/{operation_id}"' in api
    assert "Appareil non enregistré" in api
    assert "autre établissement" in api
    assert "decide_apply" in api
    assert 'op.status = "applied"' in api


def test_v18_release_states_the_business_mutation_boundary():
    release = (ROOT / "docs/RELEASE_1.8.md").read_text(encoding="utf8")
    assert "ne modifie pas encore les tables métier" in release
    assert "conflits" in release
