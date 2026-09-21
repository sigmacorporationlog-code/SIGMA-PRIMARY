"""Regression : crash au demarrage sur un .env avec CORS_ORIGINS non-JSON.

Bug reel observe: pydantic-settings exige du JSON strict pour tout champ
list[]/dict[] lu depuis .env. Un .env rempli a la main (ou genere par un
outil tiers) avec une valeur simple comme:

    CORS_ORIGINS=http://localhost:5173,http://localhost:3000

ou une ligne vide (CORS_ORIGINS=) fait planter `Settings()` avant meme le
demarrage du serveur, avec une JSONDecodeError illisible pour un non-
developpeur ("Expecting value: line 1 column 1 (char 0)"). Le serveur ne
demarre pas du tout, sur une machine qui n'a par ailleurs aucune dependance
manquante: le probleme est uniquement le format de la valeur dans .env.

Ce test verifie que Settings() accepte desormais : chaine vide, liste
separee par des virgules, JSON valide, et absence totale de la cle -- sans
jamais lever d'exception.
"""
import importlib
import sys

import pytest


def _load_settings_with_env(tmp_path, monkeypatch, env_lines):
    """Recharge app.core.config avec un .env isole pour ce test."""
    env_file = tmp_path / ".env"
    env_file.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    monkeypatch.setenv("SIGMA_DATA_DIR", str(tmp_path))

    for mod_name in ("app.core.config", "app.core.paths"):
        sys.modules.pop(mod_name, None)
    config = importlib.import_module("app.core.config")
    return config


@pytest.mark.parametrize(
    "cors_value,expected",
    [
        ("", []),
        ("   ", []),
        (
            "http://localhost:5173,http://localhost:3000",
            ["http://localhost:5173", "http://localhost:3000"],
        ),
        ('["http://localhost:5173"]', ["http://localhost:5173"]),
    ],
)
def test_cors_origins_accepts_plain_and_json_env_values(
    tmp_path, monkeypatch, cors_value, expected
):
    config = _load_settings_with_env(
        tmp_path, monkeypatch, [f"CORS_ORIGINS={cors_value}"]
    )
    settings = config.Settings()
    assert settings.CORS_ORIGINS == expected


def test_cors_origins_defaults_when_key_absent(tmp_path, monkeypatch):
    config = _load_settings_with_env(
        tmp_path, monkeypatch, ["DATABASE_URL=sqlite:///test.db"]
    )
    settings = config.Settings()
    assert settings.CORS_ORIGINS == []


def test_allowed_photo_extensions_accepts_comma_separated_env_value(
    tmp_path, monkeypatch
):
    config = _load_settings_with_env(
        tmp_path, monkeypatch, ["ALLOWED_PHOTO_EXTENSIONS=.jpg,.png,.webp"]
    )
    settings = config.Settings()
    assert settings.ALLOWED_PHOTO_EXTENSIONS == [".jpg", ".png", ".webp"]
