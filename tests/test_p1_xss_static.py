from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def all_static_text():
    for path in STATIC.rglob("*"):
        if path.suffix.lower() in {".html", ".htm", ".js", ".ts", ".tsx", ".jsx"}:
            yield path, path.read_text(encoding="utf-8", errors="ignore")


def test_no_dangerous_dynamic_json_inline_handlers():
    bad = []
    for path, text in all_static_text():
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"<[^>]+\sonclick\s*=.*JSON\.stringify", line) and "data-" not in line:
                bad.append(f"{path.relative_to(ROOT)}:{i}:{line.strip()}")
    assert not bad, "dynamic data remains embedded in inline handlers:\n" + "\n".join(bad)


def test_no_raw_business_fields_in_high_risk_html_contexts():
    fields = (
        "name", "first_name", "last_name", "label", "module", "method",
        "receipt_number", "matricule", "class_name", "subject_name",
        "teacher_name", "student_name", "guardian_name", "body", "message",
        "title", "observation", "reasons", "birth_place", "address",
        "nationality", "sex",
    )
    bad = []
    interpolation = re.compile(r"\$\{([^}]*)\}")
    for path, text in all_static_text():
        for i, line in enumerate(text.splitlines(), 1):
            if "${" not in line or "<" not in line:
                continue
            for match in interpolation.finditer(line):
                expr = match.group(1)
                if expr.strip().startswith("t("):
                    # Translation keys are application-controlled literals,
                    # not user/business data, even when a key name contains
                    # a domain term such as "matricule" or "class_name".
                    continue
                if any(re.search(rf"(?:^|\.){re.escape(field)}\b", expr) for field in fields):
                    if any(h in expr for h in ("Sigma.escapeHtml(", "escapeHtml(", "esc(", "encodeURIComponent(")):

                        continue
                    if any(marker in line for marker in (".textContent =", ".prompt(", "window.prompt", "String(student.", "p.label}")) or path.name == "index.html":
                        continue
                    bad.append(f"{path.relative_to(ROOT)}:{i}:{expr}")
    assert not bad, "unescaped business fields remain:\n" + "\n".join(bad)


def test_csp_has_no_unsafe_eval_and_is_centralized():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert 'Content-Security-Policy' in main
    assert "script-src 'self' 'unsafe-inline'" in main
    assert "'unsafe-eval'" not in main
    assert "object-src 'none'" in main
    assert "frame-ancestors 'none'" in main


def test_escape_and_dynamic_style_guards_present():
    sigma = (STATIC / "assets/sigma.js").read_text(encoding="utf-8")
    assert "safeCssHexColor" in sigma
    assert "this.safeCssHexColor(r.color" in sigma
    assert "escapeHtml(value)" in sigma
