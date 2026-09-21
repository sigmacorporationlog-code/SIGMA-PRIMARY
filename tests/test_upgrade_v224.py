from pathlib import Path
import json


def test_upgrade_service_contract():
    src = Path(__file__).parents[1] / "app/services/upgrade.py"
    text = src.read_text(encoding="utf-8")
    assert "prepare_upgrade" in text
    assert "apply_pending_upgrade" in text
    assert "create_backup" in text
    assert "command.upgrade" in text
    assert "_restore_safety_backup" in text


def test_upgrade_api_contract():
    src = Path(__file__).parents[1] / "app/api/system.py"
    text = src.read_text(encoding="utf-8")
    for endpoint in ["/upgrade/status", "/upgrade/prepare", "/upgrade/cancel"]:
        assert endpoint in text
    assert "administration.upgrade.view" in text
    assert "administration.upgrade.execute" in text


def test_startup_applies_pending_upgrade_before_schema_creation():
    src = Path(__file__).parents[1] / "app/main.py"
    text = src.read_text(encoding="utf-8")
    assert text.index("apply_pending_upgrade()") < text.index("Base.metadata.create_all")


def test_installer_version_is_release_version():
    root = Path(__file__).parents[1]
    release = json.loads((root / "release.json").read_text(encoding="utf-8"))["release"]
    assert f'MyAppVersion "{release}"' in (root / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    build = (root / "build_windows.ps1").read_text(encoding="utf-8")
    assert 'function Get-Version' in build
    assert 'release.json' in build
