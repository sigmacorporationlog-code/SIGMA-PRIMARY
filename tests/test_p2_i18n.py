import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _flatten(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(child, path))
    else:
        out[prefix] = value
    return out


def test_fr_en_catalogs_have_identical_keys():
    fr = _flatten(json.loads((ROOT / "i18n" / "fr.json").read_text(encoding="utf-8")))
    en = _flatten(json.loads((ROOT / "i18n" / "en.json").read_text(encoding="utf-8")))
    assert set(fr) == set(en)
    assert len(fr) >= 50


def test_catalog_values_are_non_empty_strings():
    for locale in ("fr", "en"):
        data = _flatten(json.loads((ROOT / "i18n" / f"{locale}.json").read_text(encoding="utf-8")))
        assert all(isinstance(v, str) and v.strip() for v in data.values())


def test_main_mounts_i18n_and_desktop_bundles_it():
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    spec = (ROOT / "sigma.spec").read_text(encoding="utf-8")
    assert 'app.mount("/i18n"' in main
    assert "'i18n'" in spec


def test_sigma_i18n_runtime_contract_and_locale_persistence():
    js = (ROOT / "static" / "assets" / "sigma.js").read_text(encoding="utf-8")
    required = [
        "i18n:",
        "async load(locale)",
        "/i18n/${wanted}.json",
        "localStorage.getItem(\"sigma_locale\")",
        "localStorage.setItem(\"sigma_locale\", next)",
        "async setLocale(locale)",
    ]
    for marker in required:
        assert marker in js
    assert "p.label ||" not in js
    assert "p.tip ||" not in js


def test_no_direct_catalog_json_in_dashboard_pages():
    dashboard = ROOT / "static" / "dashboard"
    offenders = []
    for path in dashboard.glob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"fetch\([\"']?/i18n/", text):
            offenders.append(path.name)
    assert offenders == []
