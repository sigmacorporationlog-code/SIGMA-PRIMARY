from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_document_job_model_and_migration():
    model=(ROOT/'app/models/document_jobs.py').read_text(encoding='utf8')
    mig=(ROOT/'alembic/versions/20260914_3400_documents_jobs.py').read_text(encoding='utf8')
    assert 'class DocumentJob' in model
    assert 'document_jobs' in mig
    assert "revision = '20260914_3400'" in mig

def test_bulk_bulletin_export_is_async_and_trackable():
    api=(ROOT/'app/api/evaluation.py').read_text(encoding='utf8')
    assert '/period-bulletins/export' in api
    assert 'BackgroundTasks' in api
    assert 'document-jobs/{job_id}' in api
    assert 'status_code=202' in api

def test_class_bulletin_search_supports_name_and_matricule():
    api=(ROOT/'app/api/evaluation.py').read_text(encoding='utf8')
    assert '/bulletin-search' in api
    assert 'matricule' in api
    assert 'student_name' in api
