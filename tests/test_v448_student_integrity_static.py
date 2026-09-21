from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'app/api/students.py'


def _routes():
    tree = ast.parse(SRC.read_text(encoding='utf-8'))
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr in {'get', 'post', 'patch', 'delete', 'put'}
                        and dec.args and isinstance(dec.args[0], ast.Constant)):
                    out.append((dec.func.attr.upper(), dec.args[0].value, node.name))
    return out


def test_no_duplicate_http_routes_in_students_module():
    routes = _routes()
    seen = {}
    duplicates = []
    for method, path, fn in routes:
        key = (method, path)
        if key in seen:
            duplicates.append((key, seen[key], fn))
        seen[key] = fn
    assert not duplicates, f"Routes dupliquées: {duplicates}"


def test_student_status_is_whitelisted():
    src = SRC.read_text(encoding='utf-8')
    assert 'allowed_statuses = {"active", "transferred", "dropped_out", "excluded", "graduated", "conditional"}' in src
    assert 'Statut élève invalide' in src


def test_class_creation_is_tenant_scoped():
    src = SRC.read_text(encoding='utf-8')
    assert 'if payload.school_id != current_user.school_id and not current_user.is_superadmin:' in src


def test_student_creation_validates_class_before_persistence():
    src = SRC.read_text(encoding='utf-8')
    assert src.index('school_class = None') < src.index('student = Student(**data)')
    assert 'La capacité de cette classe est atteinte' in src
