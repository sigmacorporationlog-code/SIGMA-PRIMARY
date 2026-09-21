from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v16_period_closure_and_publication_routes():
    api=(ROOT/'app/api/evaluation.py').read_text(encoding='utf8')
    model=(ROOT/'app/models/evaluation.py').read_text(encoding='utf8')
    cfg=(ROOT/'app/core/config.py').read_text(encoding='utf8')
    assert 'APP_VERSION: str = ' in cfg
    assert 'EvaluationPeriodClosure' in model
    assert '/period-finalize' in api
    assert '/period-publish' in api
    assert '/period-bulletins.zip' in api

def test_v16_closure_blocks_late_result_edits():
    api=(ROOT/'app/api/evaluation.py').read_text(encoding='utf8')
    assert 'Cette période est clôturée pour cette classe' in api
    assert 'Aucune transition supplémentaire' not in api or 'La période est clôturée' in api

def test_v16_report_card_persistence_and_ranking():
    api=(ROOT/'app/api/evaluation.py').read_text(encoding='utf8')
    academic=(ROOT/'app/models/academic.py').read_text(encoding='utf8')
    assert 'ReportCard' in api
    assert 'class_rank' in academic
    assert 'rank_map' in api
    assert 'framework.cycle != "nursery"' in api
