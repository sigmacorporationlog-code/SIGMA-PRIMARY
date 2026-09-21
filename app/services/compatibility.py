"""Compatibility client/serveur SIGMA Primaire.

La compatibilité est volontairement stricte sur le major et bornée par une
version minimale de protocole. Un client plus ancien mais encore supporté
peut synchroniser avec un serveur plus récent; un client futur ne le peut pas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
MIN_SUPPORTED_CLIENT = (2, 20, 0)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int


def parse_version(value: str) -> Version:
    if not isinstance(value, str):
        raise ValueError("Version invalide")
    m = _VERSION_RE.match(value.strip())
    if not m:
        raise ValueError(f"Version SIGMA invalide: {value}")
    return Version(*(int(x) for x in m.groups()))


def compatibility(client_version: str, server_version: str) -> dict:
    client = parse_version(client_version)
    server = parse_version(server_version)
    minimum = Version(*MIN_SUPPORTED_CLIENT)
    if client < minimum:
        return {"compatible": False, "reason": "client_too_old", "minimum_client_version": ".".join(map(str, MIN_SUPPORTED_CLIENT))}
    if client.major != server.major:
        return {"compatible": False, "reason": "major_version_mismatch", "minimum_client_version": ".".join(map(str, MIN_SUPPORTED_CLIENT))}
    if client > server:
        return {"compatible": False, "reason": "client_newer_than_server", "minimum_client_version": ".".join(map(str, MIN_SUPPORTED_CLIENT))}
    return {"compatible": True, "reason": "compatible", "minimum_client_version": ".".join(map(str, MIN_SUPPORTED_CLIENT))}
