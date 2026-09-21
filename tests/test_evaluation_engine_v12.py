from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_evaluation_activity_integrity_guards():
    src=(ROOT/'app/api/evaluation.py').read_text(encoding='utf-8')
    assert 'La période et la classe ne relèvent pas de la même année scolaire' in src
    assert 'Le coefficient doit être strictement positif' in src
    assert "Le score doit être compris entre 0 et le barème maximal" in src
    assert "Un élève absent ne peut pas avoir de score" in src
    assert "n'est pas inscrit activement dans cette classe" in src

def test_class_period_summary_endpoint_present():
    src=(ROOT/'app/api/evaluation.py').read_text(encoding='utf-8')
    assert '/classes/{class_id}/period-summary' in src
    assert 'rank' in src

def test_release_version_bumped():
    src=(ROOT/'app/core/config.py').read_text(encoding='utf-8')
    assert 'APP_VERSION: str' in src
