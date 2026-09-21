from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_uses_dist_executable_and_upgrade_stops_service_before_files():
    text = (ROOT / "installer" / "SIGMA-Setup.iss").read_text(encoding="utf-8")
    # Build « onedir » : l'exe et son dossier _internal sont copiés ensemble.
    # Un service Windows ne peut pas être servi par un build onefile (le
    # bootloader relance un processus enfant que le SCM ne surveille pas).
    assert 'Source: "..\\dist\\SIGMA-Server\\*"' in text
    assert "recursesubdirs" in text
    assert "procedure PrepareServiceForUpgrade" in text
    assert "if CurStep = ssInstall then" in text
    assert "stop {#MyServiceName}" in text
    assert "delete {#MyServiceName}" in text


def test_windows_service_reports_worker_failure_nonzero():
    text = (ROOT / "app" / "services" / "windows_service.py").read_text(encoding="utf-8")
    assert "self._worker_error = exc" in text
    assert "exit_code = 1 if self._worker_error is not None else NO_ERROR" in text
    assert "StartServiceCtrlDispatcherW(table)" in text
    assert "if not ok:" in text


def test_windows_build_compiles_inno_installer_by_default():
    text = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert "function Ensure-InnoSetup" in text
    assert "ISCC.exe" in text
    assert "installer\\SIGMA-Setup.iss" in text
    assert "SIGMA-$Version-Setup.exe" in text
