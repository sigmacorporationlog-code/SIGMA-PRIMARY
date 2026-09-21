from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def test_release_manifest():
    data = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    assert data["release"] == "4.46.0"
    assert data["ai_action_execution_default"] is False

def test_automation_files_exist():
    for p in [
        ".github/workflows/ci-windows.yml",
        ".github/workflows/ci-android.yml",
        ".github/workflows/deploy.yml",
        "scripts/build_release.py",
        "scripts/deploy_release.py",
    ]:
        assert (ROOT / p).is_file()

def test_deployment_requires_explicit_target():
    text = (ROOT / "scripts/deploy_release.py").read_text(encoding="utf-8")
    assert 'choices=("local-windows", "ssh")' in text
    assert "SIGMA_DEPLOY_HOST" in text
