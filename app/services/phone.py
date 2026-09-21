"""Validation et normalisation des numéros de téléphone au format international.

SIGMA cible des marchés francophones africains où un même établissement peut
avoir des contacts au Cameroun (+237), en France (+33), etc. Stocker et
afficher les numéros au format international (indicatif inclus) évite les
ambiguïtés lors des envois SMS réels : un numéro local sans indicatif ("6XX
XX XX XX") n'est pas exploitable tel quel par une passerelle SMS qui ne
connaît pas le pays de l'établissement.

Format accepté : E.164 assoupli — un "+" suivi de 8 à 15 chiffres au total
(recommandation UIT-T E.164). Les espaces, points et tirets de saisie sont
tolérés puis retirés ; ce n'est que la ponctuation qui est permissive, pas
l'indicatif : le "+" reste obligatoire.
"""
from __future__ import annotations

import re

_DIGITS_ONLY = re.compile(r"[\s.\-()]")
_E164_SHAPE = re.compile(r"^\+[1-9]\d{7,14}$")


class InvalidPhoneNumber(ValueError):
    """Numéro international absent ou malformé."""


def normalize_international_phone(value: str | None) -> str | None:
    """Nettoie et valide un numéro au format international.

    Retourne None si `value` est None ou une chaîne vide (le champ reste
    optionnel côté schéma). Lève InvalidPhoneNumber si une valeur non vide
    n'est pas un numéro international valide.
    """
    if value is None:
        return None
    cleaned = _DIGITS_ONLY.sub("", value.strip())
    if cleaned == "":
        return None
    if not cleaned.startswith("+"):
        raise InvalidPhoneNumber(
            f"Le numéro '{value}' doit être au format international, avec l'indicatif "
            "pays précédé de '+' (ex: +237 6XX XX XX XX)."
        )
    if not _E164_SHAPE.match(cleaned):
        raise InvalidPhoneNumber(
            f"Le numéro '{value}' n'est pas un numéro international valide "
            "(indicatif + 8 à 15 chiffres attendus, ex: +237698765432)."
        )
    return cleaned
