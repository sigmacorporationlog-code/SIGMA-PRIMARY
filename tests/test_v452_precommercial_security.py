from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_system_status_requires_system_view_permission():
    text = (ROOT / 'app/api/system.py').read_text(encoding='utf-8')
    assert '@router.get("/status", dependencies=[Depends(require_permission("administration.system.view"))])' in text


def test_release_validation_upload_is_bounded():
    text = (ROOT / 'app/api/system.py').read_text(encoding='utf-8')
    block = text[text.index('async def release_validate'):]
    assert 'max_bytes = settings.RESTORE_MAX_UPLOAD_BYTES' in block
    assert 'Package de validation trop volumineux' in block


def test_parent_portal_scopes_attendance_and_grades_to_school():
    text = (ROOT / 'app/services/parent_portal.py').read_text(encoding='utf-8')
    assert 'SchoolClass.school_id == guardian.school_id' in text
    assert 'Subject.school_id == guardian.school_id' in text
    assert '.join(SchoolClass, SchoolClass.id == Assessment.class_id)' in text


def test_sensitive_upload_endpoints_are_memory_bounded():
    students = (ROOT / 'app/api/students.py').read_text(encoding='utf-8')
    organization = (ROOT / 'app/api/organization.py').read_text(encoding='utf-8')
    assert 'MAX_IMPORT_UPLOAD_BYTES' in students
    assert 'file.file.read(max_bytes + 1)' in students
    assert 'MAX_SCHOOL_ASSET_BYTES' in organization
    assert 'Logo trop volumineux' in organization
    assert 'Cachet trop volumineux' in organization


def test_first_run_credentials_are_removed_after_password_change():
    text = (ROOT / 'app/api/auth.py').read_text(encoding='utf-8')
    assert 'first-run-credentials.txt' in text
    assert 'unlink(missing_ok=True)' in text


def test_ai_status_requires_authentication():
    text = (ROOT / 'app/api/ai.py').read_text(encoding='utf-8')
    assert 'def ai_status(current_user: User = Depends(get_current_user)):' in text
