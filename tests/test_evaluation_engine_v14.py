from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v14_bulletin_engine_and_version():
    cfg=(ROOT/"app/core/config.py").read_text(encoding="utf8")
    eng=(ROOT/"app/services/bulletin_engine.py").read_text(encoding="utf8")
    api=(ROOT/"app/api/evaluation.py").read_text(encoding="utf8")
    assert 'APP_VERSION: str' in cfg
    assert 'FINAL_STATES' in eng
    assert 'build_bulletin' in eng
    assert '/bulletin-preview' in api

def test_v14_bulletin_excludes_unvalidated_results():
    src=(ROOT/"app/services/bulletin_engine.py").read_text(encoding="utf8")
    assert 'r.get("state") in FINAL_STATES' in src
    assert 'excluded_results' in src
