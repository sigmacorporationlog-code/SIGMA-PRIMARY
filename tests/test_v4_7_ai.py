import os
os.environ.setdefault("AI_PROVIDER", "disabled")

from datetime import date

from app.core.config import settings
from app.models.ai import AIInteraction
from app.services.ai import _intent, _redact_for_provider, status


def test_ai_intents_are_deterministic():
    assert _intent("Quel est le niveau des impayés ?") == "finance_overview"
    assert _intent("Quels élèves sont à risque pédagogique ?") == "pedagogy_overview"
    assert _intent("Combien d'absences cette semaine ?") == "attendance_overview"
    assert _intent("Fais-moi une synthèse de l'école") == "school_overview"


def test_external_provider_redacts_direct_identifiers():
    payload = {"data": {"top_risks": [{"student_id": 7, "student_name": "A", "matricule": "M7", "score": 70}]}}
    redacted = _redact_for_provider(payload)
    assert redacted["data"]["top_risks"][0] == {"student_id": 7, "score": 70}


def test_ai_status_disabled_by_default():
    result = status()
    assert result["provider"] in {"disabled", "local", "openai_compatible"}
    assert "school_insight" in result["available_tools"]
    assert result["write_actions_enabled"] is False


def test_v48_status_exposes_read_only_specialized_tools():
    result = status()
    assert "finance_insight" in result["available_tools"]
    assert "attendance_insight" in result["available_tools"]
    assert "class_risk_snapshot" in result["available_tools"]
    assert "student_360" in result["available_tools"]
    assert result["write_actions_enabled"] is False


def test_v48_external_redaction_removes_sensitive_student_fields_recursively():
    payload = {"data": {"student": {"id": 4, "first_name": "A", "last_name": "B", "matricule": "M4", "birth_date": "2010-01-01"},
                          "guardians": [{"name": "Parent", "phone": "690000000"}],
                          "pedagogy": {"recent_grades": [{"score": 14, "comment": "fragile"}]}}}
    redacted = _redact_for_provider(payload)
    assert redacted["data"]["student"] == {"id": 4}
    assert redacted["data"]["guardians"] == [{}]
    assert redacted["data"]["pedagogy"]["recent_grades"] == [{"score": 14}]
