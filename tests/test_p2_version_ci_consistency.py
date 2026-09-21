import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_release_json_is_single_version_source_for_windows_ci_and_android():
    release = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    version = release['release']
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    ci = (ROOT / '.github/workflows/ci-windows.yml').read_text(encoding='utf-8')
    assert "python-version: '3.13'" in ci or 'python-version: "3.13"' in ci or 'python-version: 3.13' in ci
    gradle = (ROOT / 'mobile/android/app/build.gradle').read_text(encoding='utf-8')
    assert 'release.json' in gradle
    assert 'sigmaReleaseVersion' in gradle
    installer = (ROOT / 'build_windows.ps1').read_text(encoding='utf-8')
    assert 'release.json' in installer


def test_no_active_app_version_literals_conflict_with_release():
    version = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))['release']
    offenders = []
    for rel in [
        'app', 'scripts', 'mobile/android/app', 'installer', '.github', 'static/assets/sigma-offline.js'
    ]:
        base = ROOT / rel
        paths = base.rglob('*') if base.is_dir() else [base]
        for p in paths:
            if not p.is_file() or p.suffix not in {'.py', '.ps1', '.gradle', '.yml', '.yaml', '.js', '.json', '.iss'}:
                continue
            if any(part in {'__pycache__', 'build', 'dist'} for part in p.parts):
                continue
            text = p.read_text(errors='ignore')
            for m in re.finditer(r'\b4\.4[0-9]\.0\b', text):
                if m.group(0) != version and 'minimum_previous_release' not in text:
                    offenders.append((p.relative_to(ROOT).as_posix(), m.group(0)))
    assert offenders == []
