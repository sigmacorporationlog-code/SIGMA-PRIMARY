from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ai_knowledge_loads_sigma_before_boot():
    s = (ROOT / "static/ai-knowledge.html").read_text(encoding="utf-8")
    assert s.find('src="/dashboard/assets/sigma.js"') < s.find("Sigma.boot")


def test_context_storage_is_resilient_and_scoped():
    s = (ROOT / "static/assets/sigma.js").read_text(encoding="utf-8")
    assert "try {\n        const raw = localStorage.getItem(\"sigma_context\")" in s
    assert "ctx.academic_year_id = null; ctx.class_id = null; ctx.academic_period_id = null;" in s
    assert "ctx.class_id = null; ctx.academic_period_id = null;" in s
    assert 'classes.some(c => String(c.id) === wanted)' in s
    assert 'periods.some(p => String(p.id) === wanted)' in s


def test_offline_loader_waits_before_page_ready():
    s = (ROOT / "static/assets/sigma.js").read_text(encoding="utf-8")
    assert "const ensureOfflineReady = () =>" in s
    assert "await ensureOfflineReady();" in s


def test_dashboard_service_worker_cache_is_versioned_and_cleans_old_shells():
    s = (ROOT / "static/dashboard/sw.js").read_text(encoding="utf-8")
    assert "sigma-shell-v424" in s
    assert "caches.keys()" in s
    assert "startsWith('sigma-shell-')" in s
    assert "caches.delete(k)" in s


def test_auth_header_is_not_bearer_null():
    s = (ROOT / "static/assets/sigma.js").read_text(encoding="utf-8")
    assert 'if (this.token()) headers.Authorization = "Bearer " + this.token();' in s
    assert 'if (this.token()) retryHeaders.Authorization = "Bearer " + this.token();' in s


def test_all_protected_boot_pages_have_standard_auth_mounts():
    for name in ("ai-knowledge.html", "pilot.html"):
        s = (ROOT / "static" / name).read_text(encoding="utf-8")
        assert 'id="sigma-header"' in s
        assert 'id="login-screen"' in s
        assert 'id="main-screen"' in s


def test_shared_navigation_contains_operational_modules():
    s = (ROOT / "static/assets/sigma.js").read_text(encoding="utf-8")
    for href in ("finance.html", "operations.html", "ai-control.html"):
        assert f'/dashboard/{href}' in s
