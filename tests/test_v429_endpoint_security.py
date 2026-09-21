from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "app" / "api"

# Explicitly public by design: health/status, auth bootstrap, signed payment
# webhook, public legal documents, and badge verification. Everything else
# must resolve an authenticated user either in the handler signature or as a
# route dependency.
PUBLIC_EXCEPTIONS = {
    ("system.py", "/status"),
    ("ai.py", "/status"),
    ("payment_gateway.py", "/webhooks/{provider}"),
    ("auth.py", "/login"),
    ("auth.py", "/refresh"),
    ("auth.py", "/forgot-password"),
    ("auth.py", "/reset-password"),
    ("legal.py", "/documents"),
    ("legal.py", "/documents/{document_id}"),
    ("cards.py", "/id-cards/verify/{access_code}"),
    ("cards.py", "/badge/verify/{access_code}"),
    ("students.py", "/students/import/template.xlsx"),
    ("cloud.py", "/plans"),
    ("public_documents.py", "/verify/{token}"),
}

def _route_functions(path: Path):
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        route = None
        has_permission_dependency = False
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if not isinstance(dec.func.value, ast.Name) or dec.func.value.id != "router":
                continue
            if dec.args and isinstance(dec.args[0], ast.Constant):
                route = str(dec.args[0].value)
            text = ast.unparse(dec)
            has_permission_dependency = "require_permission" in text
            break
        if route is not None:
            yield route, node, has_permission_dependency


def test_every_protected_route_has_authentication():
    missing = []
    for path in API.glob("*.py"):
        for route, node, has_permission_dependency in _route_functions(path):
            if (path.name, route) in PUBLIC_EXCEPTIONS:
                continue
            args = {a.arg for a in node.args.args + node.args.kwonlyargs}
            if "current_user" not in args and not has_permission_dependency:
                missing.append(f"{path.name}:{route}:{node.name}")
    assert not missing, "Routes sans authentification: " + ", ".join(missing)


def test_cards_print_and_template_mutation_are_tenant_scoped():
    src = (API / "cards.py").read_text(encoding="utf-8")
    assert "_school_access(current_user, template.school_id)" in src
    assert "card = _card_access(db, current_user, card_id)" in src
    assert "_school_access(current_user, school_class.school_id)" in src
    assert "if template is None or template.school_id != school_class.school_id" in src


def test_public_badge_verification_is_rate_limited_and_minimizes_output():
    src = (API / "cards.py").read_text(encoding="utf-8")
    assert "BADGE_VERIFY_RATE_LIMIT" in src
    assert "limiter.check(" in src
    assert '"school_id": card.school_id' not in src
    assert "len(access_code) > 128" in src


def test_release_gate_declares_runtime_dependency_blockers():
    src = (ROOT / "scripts" / "release_gate.py").read_text(encoding="utf-8")
    assert "python-jose" in src
    assert "bcrypt" in src
    assert "BLOCK" in src or "FAIL" in src
