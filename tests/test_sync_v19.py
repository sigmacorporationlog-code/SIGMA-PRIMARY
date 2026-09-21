from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import apply_business_mutation


def test_v19_business_mutation_whitelists_student_fields():
    class FakeQuery:
        def filter(self, *args, **kwargs): return self
        def first(self): return SimpleNamespace(id=7, school_id=1, first_name="A", last_name="B", is_active=True)
    class FakeDB:
        def query(self, model): return FakeQuery()
    op = SimpleNamespace(operation_type="update", entity_type="student", entity_id="7", school_id=1,
                         payload={"first_name": "Grace"})
    result = apply_business_mutation(FakeDB(), op, 0)
    assert result["entity_id"] == 7


def test_v19_rejects_unknown_business_field():
    class FakeDB: pass
    op = SimpleNamespace(operation_type="update", entity_type="student", entity_id="7", school_id=1,
                         payload={"password": "bad"})
    try:
        apply_business_mutation(FakeDB(), op, 0)
    except ValueError as exc:
        assert "non autorisés" in str(exc)
    else:
        raise AssertionError("Un champ hors whitelist ne doit jamais être synchronisé")


def test_v19_create_without_required_student_fields_is_rejected():
    from tests._sync_fakes import FakeDB
    op = SimpleNamespace(operation_type="create", entity_type="student", entity_id="client-001", school_id=1, device_id="device-001", payload={"first_name":"A"})
    try:
        apply_business_mutation(FakeDB(), op, 0)
    except ValueError as exc:
        assert "obligatoires" in str(exc)
    else:
        raise AssertionError("La création offline doit exiger les champs obligatoires")


def test_v19_release_exists_and_version_is_bumped():
    cfg = (ROOT / "app/core/config.py").read_text(encoding="utf8")
    release = (ROOT / "docs/RELEASE_1.9.md").read_text(encoding="utf8")
    assert 'APP_VERSION: str = ' in cfg
    assert "mutations métier" in release
    assert "student" in release
    assert "guardian" in release
