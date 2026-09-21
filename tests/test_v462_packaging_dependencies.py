"""Garde-fous d'empaquetage Windows autonome.

Ces tests protègent les défauts qui ne se voient qu'au moment de l'installation
sur un poste vierge : une dépendance oubliée, ou un mode PyInstaller
incompatible avec le Gestionnaire de services Windows.
"""
from pathlib import Path
import ast
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

# Nom du module importé -> nom du paquet déclaré dans requirements.txt
MODULE_TO_DISTRIBUTION = {
    "PIL": "pillow",
    "docx": "python-docx",
    "jose": "python-jose",
    "multipart": "python-multipart",
    "pydantic_settings": "pydantic-settings",
    "email_validator": "email-validator",
}


def _declared_distributions() -> set[str]:
    declared = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<>=!\[;\s]", line, maxsplit=1)[0]
        declared.add(name.lower().replace("_", "-"))
    return declared


def _imported_modules() -> set[str]:
    modules = set()
    for path in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules


def test_every_third_party_import_is_declared_in_requirements():
    """Une dépendance non déclarée casse l'exécutable, pas le développement.

    C'est exactement ce qui s'était produit avec email-validator : pydantic
    l'importe paresseusement pour EmailStr, il était présent sur la machine de
    développement et absent de requirements.txt, donc absent du build gelé.
    """
    declared = _declared_distributions()
    missing = []
    for module in sorted(_imported_modules()):
        if module in sys.stdlib_module_names or module == "app":
            continue
        distribution = MODULE_TO_DISTRIBUTION.get(module, module).lower().replace("_", "-")
        if distribution not in declared:
            missing.append(f"{module} (paquet attendu: {distribution})")
    assert not missing, "Dépendances importées mais non déclarées: " + ", ".join(missing)


def test_email_validator_is_declared_because_emailstr_is_used():
    security = (ROOT / "app/schemas/security.py").read_text(encoding="utf-8")
    assert "EmailStr" in security
    assert "email-validator" in (ROOT / "requirements.txt").read_text(encoding="utf-8")


def test_spec_builds_onedir_because_onefile_cannot_host_a_windows_service():
    """En onefile, le bootloader relance un processus enfant ; le SCM surveille
    le parent, qui n'appelle jamais StartServiceCtrlDispatcherW, et le service
    échoue avec l'erreur 1053."""
    spec = (ROOT / "sigma.spec").read_text(encoding="utf-8")
    assert "COLLECT(" in spec
    assert "exclude_binaries=True" in spec
    # En onefile, EXE() reçoit a.binaries et a.datas directement.
    exe_block = spec[spec.index("exe = EXE("):spec.index("coll = COLLECT(")]
    assert "a.binaries" not in exe_block


def test_service_binpath_quotes_the_executable_path():
    """Sans guillemets échappés, sc.exe coupe « C:\\Program Files\\SIGMA\\... »
    sur l'espace et le service ne démarre jamais."""
    installer = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    assert 'binPath= ""\\""{app}\\{#MyAppExeName}\\"" --service""' in installer


def test_installer_parameters_use_inno_quote_doubling():
    """Inno Setup échappe un guillemet en le doublant. Une valeur commençant
    par un guillemet simple suivi d'un caractère termine la chaîne et casse la
    ligne silencieusement."""
    installer = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
    for line in installer.splitlines():
        if "Parameters:" not in line:
            continue
        value = line.split("Parameters:", 1)[1].strip()
        assert not value.startswith('""{'), f"Guillemets mal échappés: {line}"
        assert "\\\"{" not in value.replace('\\""', ""), f"Échappement non-Inno: {line}"


def test_alembic_script_location_is_anchored_on_the_bundle():
    """Un service Windows démarre dans C:\\Windows\\System32 : un
    script_location relatif serait introuvable."""
    upgrade = (ROOT / "app/services/upgrade.py").read_text(encoding="utf-8")
    assert 'set_main_option("script_location"' in upgrade
    assert 'bundle_dir() / "alembic"' in upgrade


def test_frozen_build_restores_usable_std_streams():
    """console=False met sys.stdout/sys.stderr à None : toute erreur de
    démarrage deviendrait invisible."""
    source = (ROOT / "run_server.py").read_text(encoding="utf-8")
    assert "_ensure_std_streams" in source
    assert "sigma-console.log" in source


def test_bootstrap_password_announced_to_the_installer_is_the_one_actually_seeded():
    """Le .env n'est pas chargé dans os.environ.

    `run_server.py --setup` écrit SIGMA_INITIAL_ADMIN_PASSWORD dans le .env et
    annonce ce mot de passe dans first-run-credentials.txt. Si seed.py ne le lit
    que via os.getenv(), il en génère un second, différent : l'administrateur
    reçoit un mot de passe qui ne fonctionne pas et l'installation est
    inutilisable. Le secret doit donc transiter par les settings.
    """
    from app.core.config import Settings

    assert "SIGMA_INITIAL_ADMIN_PASSWORD" in Settings.model_fields
    seed_src = (ROOT / "seed.py").read_text(encoding="utf-8")
    assert "settings.SIGMA_INITIAL_ADMIN_PASSWORD" in seed_src
    setup_src = (ROOT / "run_server.py").read_text(encoding="utf-8")
    assert "SIGMA_INITIAL_ADMIN_PASSWORD=" in setup_src
