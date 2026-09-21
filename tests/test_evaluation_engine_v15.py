from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v15_bulletin_pdf_route_and_engine():
    api=(ROOT/"app/api/evaluation.py").read_text(encoding="utf8")
    pdf=(ROOT/"app/services/pdf_engine.py").read_text(encoding="utf8")
    cfg=(ROOT/"app/core/config.py").read_text(encoding="utf8")
    assert 'APP_VERSION: str' in cfg
    assert '/bulletin.pdf' in api
    assert 'generate_bulletin_pdf' in api
    assert 'def generate_bulletin_pdf' in pdf

def test_v15_bulletin_contains_subject_and_competency_sections():
    src=(ROOT/"app/services/pdf_engine.py").read_text(encoding="utf8")
    assert 'Subjects / Matières' in src
    assert 'Competencies / Compétences' in src
    assert 'Decision / Décision' in src
