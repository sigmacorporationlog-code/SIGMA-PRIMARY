from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_installer_initializes_configuration_before_service():
    text = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert 'Parameters: "--setup"' in text
    assert 'create {#MyServiceName}' in text
    assert 'start= auto' in text
    assert 'start {#MyServiceName}' in text


def test_windows_build_fails_closed_on_pyinstaller_failure():
    text = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert '$ErrorActionPreference = "Stop"' in text
    assert 'pyinstaller.exe' in text or 'PyInstaller' in text
    assert '$LASTEXITCODE -ne 0' in text
    assert 'SIGMA-Server.exe généré avec succès.' in text


def test_windows_service_uses_programdata_for_persistent_data():
    paths = (ROOT / "app/core/paths.py").read_text(encoding="utf-8")
    assert 'PROGRAMDATA' in paths
    assert '"SIGMA"' in paths


def test_windows_service_has_stop_and_shutdown_handlers():
    text = (ROOT / "app/services/windows_service.py").read_text(encoding="utf-8")
    assert 'SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN' in text
    assert 'control in (1, 5)' in text
    assert 'self.stop_event.set()' in text


def test_pyinstaller_is_headless_and_no_upx():
    text = (ROOT / "sigma.spec").read_text(encoding="utf-8")
    assert 'console=False' in text
    assert 'upx=False' in text
