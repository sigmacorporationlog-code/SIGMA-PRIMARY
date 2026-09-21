from pathlib import Path


def test_windows_bootstrap_does_not_enable_browser_in_service_environment():
    source = Path('run_server.py').read_text(encoding='utf-8')
    assert '"OPEN_BROWSER=false"' in source
    assert '"OPEN_BROWSER=true"' not in source


def test_bootstrap_secret_is_scrubbed_from_persistent_env_after_password_change():
    config = Path('app/core/config.py').read_text(encoding='utf-8')
    auth = Path('app/api/auth.py').read_text(encoding='utf-8')
    assert 'def scrub_initial_admin_password()' in config
    assert 'SIGMA_INITIAL_ADMIN_PASSWORD=' in config
    assert 'scrub_initial_admin_password()' in auth


def test_legal_templates_are_explicitly_reported_as_pending_in_production_posture():
    source = Path('app/services/production.py').read_text(encoding='utf-8')
    assert 'Documents juridiques à finaliser' in source
    assert 'SIGMA-LICENCE' in Path('app/legal/documents.py').read_text(encoding='utf-8')
