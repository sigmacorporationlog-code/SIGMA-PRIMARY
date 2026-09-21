from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SYNC = (ROOT / 'app/services/sync.py').read_text(encoding="utf-8")
API = (ROOT / 'app/api/evaluation.py').read_text(encoding="utf-8")
OFF = (ROOT / 'static/assets/sigma-offline.js').read_text(encoding="utf-8")
UI = (ROOT / 'static/evaluations.html').read_text(encoding="utf-8")

def test_evaluation_result_is_a_first_class_sync_entity():
    assert '"evaluation_result": EvaluationResult' in SYNC
    assert '"evaluation_result": {"activity_id"' in SYNC
    assert '_validate_evaluation_result_payload' in SYNC

def test_evaluation_result_checks_membership_and_period():
    assert 'L\'élève n\'est pas inscrit dans la classe de l\'activité' in SYNC
    assert 'Période clôturée/publiée: création de résultat interdite' in SYNC

def test_evaluation_result_api_exposes_version_and_max_score():
    assert '"sync_version":versions.get(str(r.id),0) if r else 0' in API
    assert '"max_score":r.max_score if r and r.max_score is not None else a.max_score' in API

def test_offline_evaluation_uses_evaluation_result_protocol():
    assert "entity_type:'evaluation_result'" in OFF
    assert 'SigmaOffline.queueGradeBatch' in UI
    assert 'resolveConflict' in OFF
    assert '/api/sync/conflicts/' in OFF
