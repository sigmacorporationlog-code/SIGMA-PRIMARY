from datetime import datetime, timedelta, timezone

from app.models.ai_actions import AIActionProposal
from app.services.ai_actions import ALLOWED_ACTION_TYPES, _expire_if_needed


def test_v49_allowed_action_types_are_write_gate_candidates_only():
    assert "communication_draft" in ALLOWED_ACTION_TYPES
    assert "finance_reminder" in ALLOWED_ACTION_TYPES
    assert "pedagogy_remediation" in ALLOWED_ACTION_TYPES
    assert "report_generation" in ALLOWED_ACTION_TYPES


def test_v49_expiration_changes_only_proposed_actions():
    old = AIActionProposal(status="proposed", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert _expire_if_needed(old) is True
    assert old.status == "expired"


def test_v49_approved_action_is_not_expired():
    item = AIActionProposal(status="approved", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    assert _expire_if_needed(item) is False
    assert item.status == "approved"
