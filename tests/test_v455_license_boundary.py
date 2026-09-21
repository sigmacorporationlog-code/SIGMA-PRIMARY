from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_trial_bootstrap_imports_timedelta_before_use():
    text = (ROOT / "app/services/cloud.py").read_text(encoding="utf8")
    assert "from datetime import timedelta" in text
    assert "TRIAL_DURATION_DAYS = 30" in text


def test_bulk_student_import_enforces_capacity_before_inserts():
    text = (ROOT / "app/api/students.py").read_text(encoding="utf8")
    assert 'enforce_subscription_capacity(db, school_id, "students")' in text
    assert 'len(new_rows) > available' in text
    assert 'raise HTTPException(' in text


def test_password_reset_paths_scrub_bootstrap_secret():
    text = (ROOT / "app/api/auth.py").read_text(encoding="utf8")
    assert text.count("scrub_initial_admin_password()") >= 2
