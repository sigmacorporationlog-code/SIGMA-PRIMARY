"""Encodage des lanceurs zero-manipulation (.bat, .vbs, .ps1).

Un vrai echec de compilation vecu: build_windows.ps1 contenait un tiret
cadratin (em dash) encode en UTF-8 sans BOM. Windows PowerShell (5.1, celui
livre avec Windows, distinct de PowerShell 7/pwsh) lit un .ps1 sans BOM avec
la page de code ANSI active du systeme: les octets UTF-8 du tiret cadratin
sont alors relus comme plusieurs caracteres, dont l'un ressemble a un
guillemet, ce qui casse l'analyse syntaxique du script entier. L'utilisateur
ne voit qu'un "code 1" sans explication utile.

Les .bat et .vbs sont un cran plus fragiles encore: meme un BOM UTF-8 n'y est
pas fiable selon la version de Windows et la page de code active. Pour les
points d'entree "double-clic, zero manipulation", on reste donc en ASCII pur
plutot que de rejouer ce risque avec un correctif partiel.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PS1_FILES = ["build_windows.ps1", "build_windows_portable.ps1"]
BAT_VBS_FILES = [
    "BUILD_SIGMA_WINDOWS.bat", "setup.bat",
    "ARRETER_SIGMA.vbs", "BUILD_SIGMA_WINDOWS.vbs",
    "OUVRIR_SIGMA.vbs", "open_sigma.vbs",
]


def test_powershell_scripts_declare_utf8_via_bom():
    for name in PS1_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf", (
            f"{name}: BOM UTF-8 absent. Windows PowerShell 5.1 relira les "
            "accents et tirets typographiques avec la page de code ANSI du "
            "systeme, ce qui peut casser l'analyse du script (voir docstring)."
        )


def test_batch_and_vbs_launchers_stay_pure_ascii():
    for name in BAT_VBS_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        non_ascii = sorted(set(c for c in content if ord(c) > 127))
        assert not non_ascii, (
            f"{name}: caractere(s) non-ASCII trouve(s) {non_ascii}. "
            "cmd.exe et l'interpreteur VBScript classique ne garantissent pas "
            "un decodage UTF-8 fiable pour un lanceur double-clic : utilisez "
            "uniquement des caracteres ASCII dans ces fichiers."
        )
