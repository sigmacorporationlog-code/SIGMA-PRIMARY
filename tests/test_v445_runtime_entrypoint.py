from pathlib import Path
import ast
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_main_registers_each_router_individually():
    tree = ast.parse((ROOT / "app/main.py").read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "include_router":
            calls.append(node)
    assert calls
    assert all(len(call.args) == 1 for call in calls)


def test_source_setup_files_are_packaged():
    assert (ROOT / "setup.bat").exists()
    text = (ROOT / "setup.bat").read_text(encoding="ascii")
    assert "run_server.py --setup" in text
    assert "alembic upgrade head" in text


def test_setup_mode_is_dependency_lazy(tmp_path):
    tree = ast.parse((ROOT / "run_server.py").read_text(encoding="utf-8"))
    top_level_app_imports = [
        node for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and ((isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app"))
             or (isinstance(node, ast.Import) and any(alias.name.startswith("app") for alias in node.names)))
    ]
    assert not top_level_app_imports

    data_dir = tmp_path / "sigma-data"
    env = os.environ.copy()
    env["SIGMA_DATA_DIR"] = str(data_dir)
    result = subprocess.run(
        [sys.executable, "-S", "run_server.py", "--setup"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (data_dir / ".env").exists()
    assert (data_dir / "first-run-credentials.txt").exists()
