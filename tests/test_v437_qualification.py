import json
import subprocess
import sys
from pathlib import Path


def test_v438_qualification_suite_passes(tmp_path):
    out_json = tmp_path / "qualification.json"
    out_html = tmp_path / "qualification.html"
    proc = subprocess.run(
        [sys.executable, "scripts/qualification_suite.py", "--output", str(out_json), "--html-output", str(out_html)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["version"] == "4.46.0"
    assert report["qualification_status"] == "QUALIFIED"
    assert all(c["status"] == "PASS" for c in report["checks"])
    assert out_html.exists()


def test_v438_manifest_and_docs():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "release.json").read_text(encoding="utf-8"))
    assert manifest["release"] == "4.46.0"
    assert (root / "docs" / "RELEASE_4.42.md").exists()
