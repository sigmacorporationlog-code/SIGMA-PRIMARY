from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_bootstrap_secret_is_scrubbed_after_admin_creation():
    text = (ROOT / "seed.py").read_text(encoding="utf-8")
    assert "SIGMA_INITIAL_ADMIN_PASSWORD=" in text
    assert "_scrub_windows_initial_password" in text
    assert "env_path.write_text" in text


def test_windows_installer_restricts_programdata_permissions():
    text = (ROOT / "installer" / "SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert 'icacls.exe' in text
    assert '*S-1-5-18:(OI)(CI)F' in text
    assert '*S-1-5-32-544:(OI)(CI)F' in text
