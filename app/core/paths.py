r"""
Résolution des chemins de SIGMA, compatible à la fois avec :
  - une exécution normale depuis les sources (`python -m uvicorn ...`) ;
  - un exécutable autonome créé avec PyInstaller (`SIGMA-Server.exe`).

Deux notions distinctes :

  BUNDLE_DIR   Dossier où se trouvent les ressources embarquées en LECTURE
               SEULE (le dossier static/ notamment). En mode PyInstaller
               --onefile, c'est un dossier temporaire recréé à chaque
               lancement (sys._MEIPASS) : on n'y écrit jamais rien.

  DATA_DIR     Dossier où SIGMA doit ÉCRIRE ses données qui doivent survivre
               d'un lancement à l'autre : la base SQLite, les photos
               importées, le fichier .env. En Windows gelé, il est placé dans
               %PROGRAMDATA%\SIGMA ; en développement il reste dans le projet.
               Jamais dans le dossier temporaire d'extraction.
"""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True si le code tourne depuis un .exe généré par PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    if is_frozen():
        # PyInstaller expose ce dossier temporaire d'extraction via _MEIPASS
        # (mode --onefile) ; en mode --onedir, c'est le dossier de l'exe.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # Développement: racine du projet (deux niveaux au-dessus de ce fichier)
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    # En production Windows, les données doivent rester hors de Program Files
    # afin que SIGMA puisse écrire sans demander des droits administrateur.
    override = os.getenv("SIGMA_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    if is_frozen():
        if os.name == "nt":
            path = Path(os.getenv("PROGRAMDATA", Path.home())) / "SIGMA"
            path.mkdir(parents=True, exist_ok=True)
            return path
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def static_dir() -> Path:
    return bundle_dir() / "static"
