"""Source de vérité de version SIGMA.

Le manifeste release.json est la seule source éditable de version. Le code
charge ce manifeste aussi bien depuis le workspace source que depuis un
bundle PyInstaller onedir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


RELEASE_MANIFEST_NAME = "release.json"


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / RELEASE_MANIFEST_NAME,
        Path(sys.executable).resolve().parent / RELEASE_MANIFEST_NAME,
        Path.cwd() / RELEASE_MANIFEST_NAME,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / RELEASE_MANIFEST_NAME)
    return list(dict.fromkeys(candidates))


def load_release_manifest() -> dict[str, Any]:
    for path in _candidate_paths():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            release = str(data.get("release", "")).strip()
            product = str(data.get("product", "SIGMA")).strip()
            if release:
                data["product"] = product or "SIGMA"
                data["release"] = release
                return data
        except (OSError, ValueError, TypeError):
            continue
    raise RuntimeError("release.json introuvable ou invalide: impossible de déterminer la version SIGMA")


RELEASE = load_release_manifest()
APP_VERSION = str(RELEASE["release"])
CHANNEL = str(RELEASE.get("channel", "commercial"))
TITLE = str(RELEASE.get("title", "SIGMA"))
MINIMUM_PREVIOUS_RELEASE = str(RELEASE.get("minimum_previous_release", ""))
