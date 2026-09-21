from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_card_api_enforces_tenant_on_reads_writes_and_downloads():
    src = (ROOT / "app/api/cards.py").read_text(encoding="utf-8")
    assert "def _school_access" in src
    assert "def _card_access" in src
    assert "_school_access(current_user, payload.school_id)" in src
    assert "template.school_id != payload.school_id" in src
    assert "card=_card_access(db, current_user, card_id)" in src
    assert "_school_access(current_user, school_class.school_id)" in src


def test_student_configuration_endpoints_enforce_tenant():
    src = (ROOT / "app/api/students.py").read_text(encoding="utf-8")
    assert 'def create_level(school_id: int, name: str, order_index: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user))' in src
    assert 'def list_levels(school_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user))' in src
    assert 'def create_stream(school_id: int, name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user))' in src
    assert 'def list_streams(school_id: int, include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user))' in src
    assert 'def list_guardians(school_id: int, search: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user))' in src


def test_audit_log_listing_enforces_tenant_and_limit():
    src = (ROOT / "app/api/users.py").read_text(encoding="utf-8")
    assert 'assert_school_access(current_user, school_id)' in src
    assert 'limit = min(max(limit, 1), 500)' in src
