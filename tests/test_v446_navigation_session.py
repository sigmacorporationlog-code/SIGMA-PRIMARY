from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def test_session_token_is_persisted_and_restored_between_html_navigations():
    text = (STATIC / "assets/sigma.js").read_text(encoding="utf-8")
    assert "sessionStorage.setItem(\"sigma_access_token\"" in text
    assert "sessionStorage.getItem(\"sigma_access_token\"" in text
    assert "this._restoreAccessToken();" in text
    assert "this._persistAccessToken();" in text


def test_boot_does_not_crash_when_optional_auth_mounts_are_missing():
    text = (STATIC / "assets/sigma.js").read_text(encoding="utf-8")
    assert 'if (login) login.style.display = "none";' in text
    assert 'if (main) main.style.display = "block";' in text


def test_ai_knowledge_loads_shared_sigma_runtime():
    text = (STATIC / "ai-knowledge.html").read_text(encoding="utf-8")
    assert '/dashboard/assets/sigma.js' in text


def test_shared_navigation_contains_primary_user_workspaces():
    text = (STATIC / "assets/sigma.js").read_text(encoding="utf-8")
    for href in ("teacher.html", "parent.html", "insight.html", "administration.html"):
        assert f"/dashboard/{href}" in text
