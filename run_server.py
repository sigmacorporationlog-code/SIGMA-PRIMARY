"""SIGMA Server entrypoint for console and native Windows Service modes."""
from __future__ import annotations

import argparse
import logging
import os
import secrets
import sys
import threading
import time
import webbrowser
from pathlib import Path

SERVICE_NAME = "SIGMAPrimaireServer"


def _settings():
    from app.core.config import settings
    return settings


def _data_dir() -> Path:
    # Keep --setup usable before the application dependencies are installed.
    override = os.getenv("SIGMA_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    elif getattr(sys, "frozen", False) and os.name == "nt":
        path = Path(os.getenv("PROGRAMDATA", Path.home())) / "SIGMA"
    else:
        path = Path(__file__).resolve().parent
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_std_streams() -> None:
    """Rétablit des flux utilisables dans un build fenêtré.

    PyInstaller met sys.stdout et sys.stderr à None quand l'exécutable est
    compilé sans console (console=False). logging, uvicorn et alembic écrivent
    alors dans le vide, et la moindre erreur de démarrage devient invisible :
    le service semble « démarré » sans jamais répondre. On les redirige vers un
    fichier journal placé à côté des données.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        stream = open(_data_dir() / "sigma-console.log", "a", encoding="utf-8", buffering=1)
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def setup_windows_installation() -> int:
    """Prépare une installation Windows sans importer FastAPI/SQLAlchemy."""
    root = _data_dir()
    env_path = root / ".env"
    if env_path.exists():
        print(f"Configuration existante conservée : {env_path}")
        return 0

    secret_key = secrets.token_urlsafe(48)
    # Aucun secret partagé ne doit être embarqué dans le produit.
    # Le mot de passe bootstrap est aléatoire et n'est conservé que dans le
    # .env temporaire, puis supprimé par seed.py après création du compte.
    initial_password = os.getenv("SIGMA_INITIAL_ADMIN_PASSWORD") or secrets.token_urlsafe(24)
    env_path.write_text(
        "\n".join([
            "ENV=production",
            # Le service Windows tourne en session 0 : aucun navigateur ne doit
            # y être lancé. Le mode portable est traité séparément, voir
            # _portable_browser_enabled().
            "OPEN_BROWSER=false",
            # Déploiement LAN : le serveur doit être joignable depuis les
            # postes clients de l'établissement (http://IP-DU-SERVEUR:8000/),
            # pas seulement depuis lui-même. 0.0.0.0 écoute sur toutes les
            # interfaces réseau ; le poste serveur continue de fonctionner
            # normalement via http://127.0.0.1:8000/ (0.0.0.0 inclut la boucle
            # locale). L'installateur ouvre le port 8000 dans le pare-feu
            # Windows (voir installer/SIGMA-Setup.iss) pour que ça marche
            # réellement, pas seulement en théorie.
            "BIND_HOST=0.0.0.0",
            "PORT=8000",
            # Sert de base aux liens envoyés par email (réinitialisation de
            # mot de passe). Reste en loopback par défaut : un lien construit
            # sur l'IP LAN ne serait valable que tant que cette IP ne change
            # pas (DHCP). Si la récupération de mot de passe par email est
            # activée (SMTP_HOST renseigné) pour des comptes qui se
            # connectent depuis d'autres postes, remplacez cette valeur par
            # http://IP-DU-SERVEUR:8000 dans le .env.
            "PUBLIC_BASE_URL=http://127.0.0.1:8000",
            "AUTH_COOKIE_SECURE=false",
            f"SECRET_KEY={secret_key}",
            f"SIGMA_INITIAL_ADMIN_PASSWORD={initial_password}",
            "MAX_BACKUPS_TO_KEEP=30",
            "",
        ]),
        encoding="utf-8",
    )
    report = root / "first-run-credentials.txt"
    report.write_text(
        "SIGMA — PREMIÈRE INSTALLATION\n\n"
        "Compte administrateur initial\n"
        "Utilisateur : admin\n"
        f"Mot de passe : {initial_password}\n\n"
        "IMPORTANT : connectez-vous immédiatement et changez ce mot de passe.\n"
        "Ce fichier contient un secret : supprimez-le après la première connexion.\n",
        encoding="utf-8",
    )
    print(f"Installation SIGMA préparée dans : {root}")
    print(f"Identifiants initiaux enregistrés dans : {report}")
    print(f"Compte initial -> utilisateur: admin | mot de passe: {initial_password} (à changer à la première connexion)")
    return 0


def _ensure_first_run_config() -> Path | None:
    """Auto-configure un exécutable Windows portable au premier lancement."""
    if not (getattr(sys, "frozen", False) and os.name == "nt"):
        return None
    root = _data_dir()
    env_path = root / ".env"
    if env_path.exists():
        return None
    setup_windows_installation()
    return root / "first-run-credentials.txt"


def _portable_browser_enabled(settings) -> bool:
    """Décide si un lancement console/portable doit ouvrir le tableau de bord.

    Le .env généré force OPEN_BROWSER=false pour le service Windows (session 0,
    aucun bureau). Mais un double-clic sur SIGMA-Server.exe n'affiche rien du
    tout : il faut alors ouvrir le navigateur. Une variable d'environnement
    OPEN_BROWSER explicite (utilisée par le smoke test de compilation) reste
    prioritaire et permet de refuser cette ouverture.
    """
    if settings.OPEN_BROWSER:
        return True
    if os.getenv("OPEN_BROWSER") is not None:
        return False
    return bool(getattr(sys, "frozen", False) and os.name == "nt")


STOP_REQUEST_FILE = "sigma-stop.request"


def _stop_request_path() -> Path:
    return _data_dir() / STOP_REQUEST_FILE


def _watch_stop_request(stop_event: threading.Event) -> None:
    """Permet d'arrêter proprement un serveur lancé sans console.

    Le paquet portable est compilé sans terminal : il n'y a ni Ctrl+C ni icône
    de zone de notification pour l'arrêter, et un arrêt forcé du processus
    n'est pas souhaitable. On surveille donc un fichier sentinelle déposé par
    `SIGMA-Server.exe --stop` ; sa détection déclenche l'arrêt normal d'Uvicorn
    (fermeture des connexions et de la base), puis le fichier est retiré pour
    signaler que l'arrêt est effectif.
    """
    path = _stop_request_path()
    while not stop_event.wait(1.0):
        try:
            if path.exists():
                stop_event.set()
        except OSError:
            continue


def request_stop(timeout_seconds: float = 30.0) -> int:
    """Demande l'arrêt d'un serveur SIGMA lancé en mode console/portable."""
    path = _stop_request_path()
    try:
        path.write_text("stop", encoding="utf-8")
    except OSError as exc:
        print(f"Impossible de demander l'arrêt : {exc}")
        return 1
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not path.exists():
            print("SIGMA est arrêté.")
            return 0
        time.sleep(0.5)
    print("Aucun serveur SIGMA n'a répondu à la demande d'arrêt.")
    path.unlink(missing_ok=True)
    return 2


def _ensure_database_ready() -> None:
    try:
        import seed
        seed.run()
    except Exception as exc:
        logging.getLogger(__name__).warning("Initialisation des données ignorée: %s", exc)


def _open_browser_when_ready(port: int) -> None:
    time.sleep(1.5)
    try:
        webbrowser.open(f"http://127.0.0.1:{port}/dashboard/")
    except Exception:
        pass


def _run_uvicorn(stop_event: threading.Event, host: str, port: int, app, open_browser: bool = False) -> None:
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    def watcher() -> None:
        stop_event.wait()
        server.should_exit = True

    threading.Thread(target=watcher, daemon=True).start()
    if open_browser:
        threading.Thread(target=_open_browser_when_ready, args=(port,), daemon=True).start()
    server.run()


def run_console() -> None:
    first_run_report = _ensure_first_run_config()
    settings = _settings()
    from app.main import app as fastapi_app

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    print("== SIGMA Server ==")
    print(f"Version : {settings.APP_VERSION}")
    print(f"Dossier de données : {_data_dir()}")
    open_browser = _portable_browser_enabled(settings)
    if first_run_report and first_run_report.exists() and open_browser:
        try:
            os.startfile(str(first_run_report))
        except Exception:
            pass
    _ensure_database_ready()
    stop = threading.Event()
    # Une demande d'arrêt laissée par une exécution précédente arrêterait le
    # serveur aussitôt démarré.
    try:
        _stop_request_path().unlink(missing_ok=True)
    except OSError:
        pass
    threading.Thread(target=_watch_stop_request, args=(stop,), daemon=True).start()
    try:
        _run_uvicorn(stop, settings.BIND_HOST, settings.PORT, fastapi_app, open_browser=open_browser)
    except KeyboardInterrupt:
        stop.set()
    finally:
        stop.set()
        # Retrait synchrone : le thread de surveillance est un démon et le
        # processus se termine juste après, il ne faut pas compter sur lui pour
        # signaler que l'arrêt est effectif.
        try:
            _stop_request_path().unlink(missing_ok=True)
        except OSError:
            pass


def run_windows_service() -> int:
    settings = _settings()
    from app.main import app as fastapi_app
    from app.services.windows_service import WindowsServiceHost

    data = _data_dir()
    logging.basicConfig(
        filename=str(data / "sigma-service.log"),
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    def worker(stop_event: threading.Event) -> None:
        _ensure_database_ready()
        _run_uvicorn(stop_event, settings.BIND_HOST, settings.PORT, fastapi_app, open_browser=False)

    host = WindowsServiceHost(SERVICE_NAME, worker)
    return host.run()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--service", action="store_true", help="lancer sous le Gestionnaire de services Windows")
    parser.add_argument("--setup", action="store_true", help="préparer une installation Windows commerciale")
    parser.add_argument("--stop", action="store_true", help="arrêter proprement un serveur lancé en mode portable")
    args = parser.parse_args()
    _ensure_std_streams()
    if args.setup:
        sys.exit(setup_windows_installation())
    if args.stop:
        sys.exit(request_stop())
    if args.service:
        sys.exit(run_windows_service())
    run_console()


if __name__ == "__main__":
    main()
