from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def test_shared_escape_html_exists():
    text = (STATIC / "assets" / "sigma.js").read_text(encoding="utf-8")
    assert "escapeHtml(value)" in text


def test_high_risk_pages_do_not_render_known_pii_without_escaping():
    checks = {
        "communication.html": ["${l.body}", "${l.recipient_label}", "${x.name||x.label"],
        "parent.html": ["${me.first_name}", "${r.period_name}", "${r.appreciation}", "${g.subject}", "${g.assessment}"],
        "teacher.html": ["${c.class_name}", "${c.subject_name}", "${a.name}", "${a.class_name}"],
    }
    for name, forbidden in checks.items():
        text = (STATIC / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"Unsafe dynamic interpolation remains in {name}: {token}"


def test_insight_internal_links_are_constrained():
    text = (STATIC / "insight.html").read_text(encoding="utf-8")
    assert "function safeInternalHref" in text
    assert "safeInternalHref(a.href)" in text
