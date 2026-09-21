from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_boot_restores_refresh_session_before_login_screen():
    js = (ROOT / "static/assets/sigma.js").read_text(encoding="utf-8")
    assert "if (!refreshAttempted && await this.refresh())" in js
    assert "this._refreshPromise" in js
    # A fresh HTML navigation must not immediately render the login screen.
    assert "if (!this._accessToken) return this.renderLoginScreen(showMain);" not in js


def test_windows_setup_binds_all_interfaces_for_lan_with_http_cookie_exception():
    # Déploiement LAN commercial : le serveur doit être joignable depuis les
    # postes clients de l'établissement, pas seulement depuis lui-même.
    source = (ROOT / "run_server.py").read_text(encoding="utf-8")
    assert '"BIND_HOST=0.0.0.0"' in source
    assert '"AUTH_COOKIE_SECURE=false"' in source
    # PUBLIC_BASE_URL reste en loopback par défaut (liens email stables,
    # indépendants de l'IP LAN attribuée par DHCP) ; voir le commentaire
    # au-dessus de cette ligne dans run_server.py pour l'ajuster si la
    # récupération de mot de passe par email est activée.
    assert '"PUBLIC_BASE_URL=http://127.0.0.1:8000"' in source


def test_installer_opens_lan_firewall_port_for_client_workstations():
    # BIND_HOST=0.0.0.0 seul ne suffit pas : sans règle de pare-feu, Windows
    # bloque par défaut les connexions entrantes vers un nouveau programme,
    # et les postes clients du LAN ne peuvent pas joindre le serveur.
    iss = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert "netsh.exe" in iss
    assert "advfirewall firewall add rule" in iss
    assert "localport=8000" in iss
    assert "dir=in action=allow" in iss
    # La règle est supprimée à la désinstallation, comme le service.
    assert iss.count("advfirewall firewall delete rule") >= 2


def test_refresh_cookie_security_is_explicitly_configurable():
    auth = (ROOT / "app/api/auth.py").read_text(encoding="utf-8")
    config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
    assert "AUTH_COOKIE_SECURE: bool | None = None" in config
    assert "def _refresh_cookie_secure()" in auth
    assert auth.count("secure=_refresh_cookie_secure()") == 2


def test_windows_spec_embeds_runtime_resources():
    spec = (ROOT / "sigma.spec").read_text(encoding="utf-8")
    for required in ["'static'", "'alembic'", "'alembic.ini'", "'release.json'"]:
        assert required in spec
    assert "console=False" in spec


def test_portable_build_has_runtime_smoke_test_and_hash():
    ps = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert "PyInstaller" in ps
    assert "/api/health/live" in ps
    assert "/dashboard/" in ps
    assert "Get-FileHash -Algorithm SHA256" in ps
    assert "Compress-Archive" in ps
    assert "requirements-build.txt" in ps


def test_no_html_bytes_after_closing_document():
    for page in (ROOT / "static").glob("*.html"):
        text = page.read_text(encoding="utf-8", errors="ignore")
        idx = text.lower().find("</html>")
        if idx >= 0:
            assert not text[idx + len("</html>"):].strip(), page.name


def test_sensitive_dashboard_pages_use_sigma_boot_and_api():
    for name in ["ai-control.html", "insight.html", "operations.html"]:
        text = (ROOT / "static" / name).read_text(encoding="utf-8")
        assert "/dashboard/assets/sigma.js" in text
        assert "Sigma.boot(" in text
        assert "Sigma.api(" in text
