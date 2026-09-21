from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_is_loaded_from_release_manifest():
    manifest = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    from app.core.version import APP_VERSION
    assert APP_VERSION == manifest["release"]


def test_windows_ci_uses_python_313():
    src = (ROOT / ".github/workflows/ci-windows.yml").read_text(encoding="utf-8")
    assert "python-version: '3.13'" in src
    assert "python-version: '3.12'" not in src


def test_offline_registration_does_not_embed_old_hardcoded_version():
    src = (ROOT / "static/assets/sigma-offline.js").read_text(encoding="utf-8")
    assert "2.17.0-primary-commercial" not in src
    assert "/api/version" in src
