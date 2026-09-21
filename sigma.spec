# -*- mode: python ; coding: utf-8 -*-
# SIGMA Windows standalone PyInstaller specification.
#
# MODE « ONEDIR » (un dossier), et non « onefile ».
# ---------------------------------------------------------------------------
# C'est un choix imposé par le mode service Windows. En mode onefile, le
# bootloader PyInstaller décompresse l'archive dans %TEMP% puis RELANCE
# l'exécutable dans un processus ENFANT. Or le Gestionnaire de services
# (SCM) ne surveille que le processus qu'il a lui-même démarré : c'est le
# processus parent, qui n'appelle jamais StartServiceCtrlDispatcherW. Le SCM
# considère alors que le service n'a pas répondu et échoue avec l'erreur
# 1053 (« Le service n'a pas répondu assez vite »), tandis que l'enfant
# reçoit ERROR_FAILED_SERVICE_CONTROLLER_CONNECT (1063).
# En mode onedir, l'exécutable est le processus réel : le service démarre.
# Avantages annexes : démarrage plus rapide (aucune extraction à chaque
# lancement) et beaucoup moins de faux positifs antivirus.
# Le PC cible n'a toujours AUCUNE dépendance à installer : l'interpréteur
# Python, les modules natifs, le tableau de bord et les migrations sont
# livrés dans le dossier de l'application.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / 'static'), 'static'),
    (str(ROOT / 'alembic'), 'alembic'),
    (str(ROOT / 'alembic.ini'), '.'),
    (str(ROOT / 'release.json'), '.'),
    (str(ROOT / 'i18n'), 'i18n'),
]

# Icône SIGMA (symbole Sigma vert/orange de la charte graphique), embarquée
# dans l'exécutable lui-même. C'est elle qui apparaît dans la barre des
# tâches Windows dès que le processus SIGMA-Server.exe est visible (ex:
# épinglé), et c'est elle que reprennent les raccourcis Bureau / menu
# Démarrer créés par l'installateur (voir installer/SIGMA-Setup.iss).
ICON_PATH = str(ROOT / 'assets' / 'sigma.ico')

# uvicorn choisit ses implémentations HTTP/WebSocket/lifespan/boucle
# d'événements au moment de l'exécution, via importlib et des chaînes de
# caractères ("uvicorn.protocols.http.auto:AutoHTTPProtocol", etc. — voir
# uvicorn/config.py, dictionnaires HTTP_PROTOCOLS/WS_PROTOCOLS/LIFESPAN/
# LOOP_FACTORIES). L'analyse statique de PyInstaller ne voit jamais ces
# chaînes : sans cette ligne, ces sous-modules sont absents de l'exécutable
# et SIGMA-Server.exe plante au démarrage (ModuleNotFoundError) sur la
# machine cible, alors que "python run_server.py" fonctionnait très bien
# en développement.
#
# Même raisonnement pour :
#   - alembic     : les dialectes DDL et les commandes sont résolus par nom ;
#   - sqlalchemy  : les dialectes sont chargés depuis un registre de chaînes ;
#   - email_validator : importé paresseusement par pydantic pour EmailStr ;
#   - httpx / pywebpush : importés dans le corps de fonctions optionnelles.
hiddenimports = (
    collect_submodules('app')
    + collect_submodules('uvicorn')
    + collect_submodules('alembic')
    + collect_submodules('sqlalchemy.dialects')
    + ['seed', 'email_validator', 'httpx', 'pywebpush']
)

a = Analysis(
    ['run_server.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest', '_pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SIGMA-Server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=ICON_PATH,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='SIGMA-Server',
)
