from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_runtime_files_exist():
    required = [
        "run_server.py", "sigma.spec", "requirements.txt", "seed.py",
        "app/main.py", "static/index.html", "static/students.html",
        "static/academic.html", "static/evaluations.html",
        "static/administration.html", "static/finance.html",
        "static/cards.html", "static/communication.html",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Fichiers runtime manquants: {missing}"


def test_commercial_packaging_is_headless():
    spec = (ROOT / "sigma.spec").read_text(encoding="utf-8")
    assert "console=False" in spec
    installer = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert "SIGMA-Server.exe" in installer
    assert "8000" in installer
