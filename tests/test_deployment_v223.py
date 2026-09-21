from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
INSTALLER = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
SPEC = (ROOT / "sigma.spec").read_text(encoding="utf-8")
BUILD = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")


def test_version_bumped_everywhere():
    import json
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))["release"]
    assert 'APP_VERSION: str' in CONFIG
    assert f'#define MyAppVersion "{release}"' in INSTALLER
    assert 'function Get-Version' in BUILD
    assert 'release.json' in BUILD


def test_windows_build_is_explicitly_windows_only():
    assert '$env:OS -ne "Windows_NT"' in BUILD
    assert 'SIGMA-Server.exe' in BUILD and 'absent' in BUILD


def test_pyinstaller_build_does_not_require_upx():
    assert 'upx=False' in SPEC


def test_installer_targets_service_executable():
    assert 'SIGMAPrimaireServer' in INSTALLER
    assert 'binPath=' in INSTALLER
    # sc.exe découpe binPath sur les espaces : « C:\Program Files\SIGMA\... »
    # doit donc être entouré de guillemets échappés (\") à l'intérieur de la
    # valeur, elle-même entre guillemets doublés au sens Inno Setup ("").
    assert 'binPath= ""\\""{app}\\{#MyAppExeName}\\"" --service""' in INSTALLER
