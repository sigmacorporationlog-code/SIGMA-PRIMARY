from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ai_action_links_interaction_only_within_authorized_school():
    text = (ROOT / "app/services/ai_actions.py").read_text(encoding="utf-8")
    assert "interaction = db.get(AIInteraction, ai_interaction_id)" in text
    assert "interaction.school_id != user.school_id" in text


def test_ai_action_approval_and_rejection_require_elevated_permission():
    text = (ROOT / "app/services/ai_actions.py").read_text(encoding="utf-8")
    approve = text[text.index("def approve("):text.index("def reject(")]
    reject = text[text.index("def reject("):text.index("def _assert_execute(")]
    assert "user_has_permission(db, user, AI_EXECUTE_PERMISSION)" in approve
    assert "user_has_permission(db, user, AI_EXECUTE_PERMISSION)" in reject


def test_ai_knowledge_governance_requires_elevated_permission():
    text = (ROOT / "app/api/ai_knowledge.py").read_text(encoding="utf-8")
    assert 'AI_GOVERN_PERMISSION = "administration.ai.execute"' in text
    state = text[text.index('@router.post("/documents/{document_id}/state")'):text.index('@router.patch("/documents/{document_id}/governance")')]
    governance = text[text.index('@router.patch("/documents/{document_id}/governance")'):text.index('@router.post("/search")')]
    assert "_allowed(db, current_user, AI_GOVERN_PERMISSION)" in state
    assert "_allowed(db, current_user, AI_GOVERN_PERMISSION)" in governance


def test_ai_external_prompt_explicitly_treats_sigma_context_as_non_authoritative():
    text = (ROOT / "app/services/ai.py").read_text(encoding="utf-8")
    assert "sans inventer de données" in text
    assert "Utilise uniquement le contexte SIGMA fourni" in text
    assert "de décision administrative à la place" in text
