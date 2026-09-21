from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sync_student_creation_is_quota_guarded():
    src = (ROOT / 'app/services/sync.py').read_text(encoding='utf-8')
    block = src[src.index('elif operation.entity_type == "student":'):src.index('elif operation.entity_type == "guardian":')]
    assert 'enforce_subscription_capacity(db, operation.school_id, "students")' in block
    assert 'SubscriptionError' in block


def test_sync_student_reactivation_is_quota_guarded():
    src = (ROOT / 'app/services/sync.py').read_text(encoding='utf-8')
    assert 'field == "status" and raw_value == "active" and entity.status != "active"' in src
    assert 'enforce_subscription_capacity(db, operation.school_id, "students")' in src


def test_http_student_reactivation_is_quota_guarded():
    src = (ROOT / 'app/api/students.py').read_text(encoding='utf-8')
    block = src[src.index('def change_student_status'):src.index('@router.post("/students/{student_id}/withdraw"')]
    assert 'new_status == "active" and old_status != "active"' in block
    assert 'enforce_subscription_capacity(db, student.school_id, "students")' in block


def test_restore_preserves_live_subscription_state():
    src = (ROOT / 'app/services/backup.py').read_text(encoding='utf-8')
    assert 'def _preserve_and_validate_commercial_state' in src
    assert 'ATTACH DATABASE ? AS live_db' in src
    assert 'DELETE FROM school_subscriptions' in src
    assert 'INSERT INTO school_subscriptions' in src
    assert 'quota_violations' in src
    assert '_preserve_and_validate_commercial_state(new_db)' in src


def test_subscription_usage_validator_exists():
    src = (ROOT / 'app/services/cloud.py').read_text(encoding='utf-8')
    assert 'def validate_subscription_usage' in src
    assert 'users > sub.max_users' in src
    assert 'students > sub.max_students' in src
