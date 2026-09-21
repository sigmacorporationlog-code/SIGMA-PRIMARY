from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_document_routes_exist():
    src=(ROOT/"app/api/students.py").read_text(encoding="utf-8")
    assert "/students/{student_id}/documents/enrollment-certificate.pdf" in src
    assert "/students/{student_id}/documents/dossier.pdf" in src
    assert "document.enrollment_certificate" in src
    assert "document.student_dossier" in src

def test_pdf_generators_exist():
    src=(ROOT/"app/services/pdf_engine.py").read_text(encoding="utf-8")
    assert "generate_enrollment_certificate_pdf" in src
    assert "generate_student_dossier_pdf" in src

def test_ui_exposes_dossier_pdf():
    src=(ROOT/"static/students.html").read_text(encoding="utf-8")
    assert "downloadDossier(${s.id})" in src
    assert "/documents/dossier.pdf" in src
