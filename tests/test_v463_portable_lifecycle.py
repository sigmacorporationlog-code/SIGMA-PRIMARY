"""Cycle de vie du paquet portable et confidentialité du secret d'amorçage."""
from pathlib import Path
import threading

import run_server

ROOT = Path(__file__).resolve().parents[1]


def test_stop_request_stops_a_running_console_server(tmp_path, monkeypatch):
    """Le paquet portable n'a ni console ni icône : l'arrêt passe par une
    sentinelle sur disque, qui doit déclencher un arrêt normal d'Uvicorn."""
    monkeypatch.setenv("SIGMA_DATA_DIR", str(tmp_path))
    stop = threading.Event()
    watcher = threading.Thread(target=run_server._watch_stop_request, args=(stop,), daemon=True)
    watcher.start()
    assert not stop.is_set()
    run_server._stop_request_path().write_text("stop", encoding="utf-8")
    assert stop.wait(5.0), "La demande d'arrêt n'a pas été détectée"


def test_stop_reports_when_no_server_is_running(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGMA_DATA_DIR", str(tmp_path))
    assert run_server.request_stop(timeout_seconds=1.0) == 2
    # La demande doit être retirée pour ne pas arrêter le prochain démarrage.
    assert not run_server._stop_request_path().exists()


def test_console_startup_clears_a_stale_stop_request():
    source = (ROOT / "run_server.py").read_text(encoding="utf-8")
    start = source.index("def run_console()")
    body = source[start:source.index("def run_windows_service()")]
    assert "_stop_request_path().unlink(missing_ok=True)" in body
    assert "_watch_stop_request" in body


def test_portable_package_ships_a_stop_launcher():
    assert (ROOT / "ARRETER_SIGMA.vbs").exists()
    build = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert "ARRETER_SIGMA.vbs" in build


def test_seed_never_prints_the_bootstrap_secret_from_a_frozen_build():
    """En build fenêtré, stdout est redirigé vers sigma-console.log : un secret
    imprimé y resterait indéfiniment, dans un fichier que personne ne purge.
    L'affichage n'est donc toléré qu'en exécution depuis les sources, dans un
    vrai terminal."""
    seed_src = (ROOT / "seed.py").read_text(encoding="utf-8")
    assert "_write_initial_credentials_report" in seed_src
    lines = seed_src.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("print(") and "{initial_password}" in stripped):
            continue
        if "enregistré dans" in stripped:
            continue
        # Toute autre impression du secret doit être gardée par un test
        # explicite sur sys.frozen dans les lignes qui précèdent.
        guard = "\n".join(lines[max(0, index - 4):index])
        assert 'getattr(sys, "frozen", False)' in guard, f"Secret imprimé sans garde-fou: {stripped}"
