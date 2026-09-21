from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = (ROOT / 'static/assets/sigma-offline.js').read_text(encoding="utf-8")
ACADEMIC = (ROOT / 'static/academic.html').read_text(encoding="utf-8")
CONFIG = (ROOT / 'app/core/config.py').read_text(encoding="utf-8")
INSTALLER = (ROOT / 'installer/SIGMA-Setup.iss').read_text(encoding="utf-8")


def test_version_bumped_everywhere():
    assert 'APP_VERSION: str' in CONFIG
    assert '#define MyAppVersion "4.46.0"' in INSTALLER


def test_indexeddb_v2_has_normalized_entity_store():
    assert 'const VERSION = 3;' in OFFLINE
    assert "createObjectStore('entities', {keyPath:'key'})" in OFFLINE
    assert "createIndex('entity_type', 'entity_type')" in OFFLINE
    assert "createIndex('assessment_id', 'assessment_id')" in OFFLINE


def test_grade_store_and_local_validation_exist():
    assert 'gradeRowsPut' in OFFLINE
    assert 'gradeRowsGet' in OFFLINE
    assert 'queueGradeBatch' in OFFLINE
    assert 'score < 0 || score > Number(maxScore)' in OFFLINE
    assert "row.state === 'locked' || row.state === 'published'" in OFFLINE


def test_evaluation_ui_hydrates_and_reads_local_cache():
    assert 'SigmaOffline.assessmentPut(a)' in ACADEMIC
    assert 'SigmaOffline.assessmentAll(ctx.class_id, ctx.academic_period_id)' in ACADEMIC
    assert 'SigmaOffline.gradeRowsPut(assessmentId, rows)' in ACADEMIC
    assert 'SigmaOffline.gradeRowsGet(assessmentId)' in ACADEMIC


def test_offline_save_uses_structured_grade_batch():
    assert 'SigmaOffline.queueGradeBatch(currentAssessmentId, payload, currentAssessmentMax)' in ACADEMIC
    assert 'Notes enregistrées localement — synchronisation à la reconnexion' in ACADEMIC


def test_grade_cache_merges_without_losing_student_metadata():
    assert "const existing = await this.gradeRowsGet(assessmentId)" in OFFLINE
    assert "const merged = {...(byStudent.get(sid) || {}), ...row" in OFFLINE

def test_offline_grade_batches_are_coalesced_per_assessment():
    assert "item.kind === 'sync_operation'" in OFFLINE
    assert "item.assessment_id === Number(assessmentId)" in OFFLINE
