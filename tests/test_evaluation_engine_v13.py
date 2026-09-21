from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_v13_state_machine_and_calculation_helpers():
    src=(ROOT/'app/services/evaluation_engine.py').read_text(encoding='utf-8')
    assert 'draft", "submitted", "checked", "validated", "locked", "published' in src
    assert 'calculate_period_results' in src
    assert 'appreciation_for_percent' in src

def test_v13_api_workflow_and_appreciation_routes():
    src=(ROOT/'app/api/evaluation.py').read_text(encoding='utf-8')
    assert '/results/transition' in src
    assert '/period-calculation' in src
    assert '/appreciation-rules' in src
    assert 'evaluation.results.validate' in src
    assert 'evaluation.results.lock' in src

def test_v13_model_rules():
    src=(ROOT/'app/models/evaluation.py').read_text(encoding='utf-8')
    assert 'class AppreciationRule' in src
    assert 'validated_by_id' in src
