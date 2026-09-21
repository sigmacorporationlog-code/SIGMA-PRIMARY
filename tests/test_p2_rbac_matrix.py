from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def _route_decorators(path: str) -> dict[str, list[str]]:
    src = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decs = [ast.get_source_segment(src, d) or "" for d in node.decorator_list]
        routes = [d for d in decs if d.startswith("router.")]
        if routes:
            out[node.name] = routes
    return out


def test_students_sensitive_routes_have_read_or_write_permission():
    routes = _route_decorators("app/api/students.py")
    for fn in ("list_students", "student_profile", "student_360", "get_student", "students_grid", "export_students_excel", "export_students_pdf", "import_students_excel"):
        blob = "\n".join(routes[fn])
        assert "require_permission(" in blob, fn


def test_admin_read_routes_use_dedicated_permissions():
    routes = _route_decorators("app/api/users.py")
    for fn in ("list_users", "get_user", "list_posts", "list_post_permissions", "list_user_posts", "list_permissions", "rbac_profiles"):
        blob = "\n".join(routes[fn])
        assert "require_permission(" in blob, fn


def test_cards_downloads_are_permission_gated():
    routes = _route_decorators("app/api/cards.py")
    for fn in ("list_cards", "download_card_pdf", "download_class_cards_pdf"):
        blob = "\n".join(routes[fn])
        assert "cards.view" in blob, fn


def test_communication_v3_reads_are_permission_gated():
    routes = _route_decorators("app/api/communication_v3.py")
    for fn in ("list_deliveries", "list_templates", "list_campaigns"):
        blob = "\n".join(routes[fn])
        assert "communication.sms.view" in blob, fn


def test_permission_catalog_has_no_duplicate_codes():
    from app.services.permission_catalog import PERMISSIONS
    codes = [p.code for p in PERMISSIONS]
    assert len(codes) == len(set(codes))
    assert "communication.sms.view" in codes
    assert "administration.ai.use" in codes
    assert "administration.ai.execute" in codes


def test_role_profile_permissions_exist_in_catalog():
    from app.services.permission_catalog import PERMISSION_BY_CODE
    from app.services.rbac_enterprise import ROLE_PROFILES
    missing = {
        role: sorted(set(spec["permissions"]) - set(PERMISSION_BY_CODE))
        for role, spec in ROLE_PROFILES.items()
    }
    assert not any(missing.values()), missing
