"""SIGMA V4.42 trusted automatic update primitives.

Update artifacts are protected in two independent layers:
1. the release manifest is authenticated with an Ed25519 signature;
2. the downloaded artifact is checked against the manifest's exact size + SHA-256.

The private signing key never belongs in the application. Only the public key
is needed by the update agent. Activation stays delegated to deployment_guard
and remains explicit/Windows-only.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import tempfile
import time
import errno
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.deployment_guard import sha256_file

logger = logging.getLogger(__name__)


class UpdateAgentError(RuntimeError):
    """Erreur fail-closed du processus de mise à jour."""


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    url: str
    sha256: str
    size_bytes: int
    channel: str = "commercial"
    min_version: str | None = None
    notes: str = ""
    key_id: str | None = None
    signature: str | None = None
    signature_algorithm: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateManifest":
        required = ("version", "url", "sha256", "size_bytes")
        if any(k not in data for k in required):
            raise UpdateAgentError("manifest incomplet")
        version = str(data["version"]).strip()
        url = str(data["url"]).strip()
        digest = str(data["sha256"]).strip().lower()
        try:
            size = int(data["size_bytes"])
        except (TypeError, ValueError) as exc:
            raise UpdateAgentError("size_bytes invalide") from exc
        if not version or len(version) > 40:
            raise UpdateAgentError("version cible invalide")
        if not (url.startswith("https://") or url.startswith("file://")):
            raise UpdateAgentError("URL de mise à jour invalide: HTTPS ou file:// uniquement")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise UpdateAgentError("SHA-256 invalide")
        if size <= 0:
            raise UpdateAgentError("taille d'artefact invalide")
        algorithm = str(data.get("signature_algorithm", "")).strip().lower() or None
        if algorithm and algorithm != "ed25519":
            raise UpdateAgentError("algorithme de signature non supporté")
        return cls(
            version,
            url,
            digest,
            size,
            str(data.get("channel", "commercial"))[:30],
            str(data["min_version"])[:40] if data.get("min_version") else None,
            str(data.get("notes", ""))[:500],
            str(data["key_id"])[:100] if data.get("key_id") else None,
            str(data["signature"]) if data.get("signature") else None,
            algorithm,
        )


def _read_manifest_dict(source: Path | str) -> dict[str, Any]:
    path = Path(source)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateAgentError("manifest illisible") from exc
    if not isinstance(data, dict):
        raise UpdateAgentError("manifest invalide")
    return data


def load_manifest(source: Path | str) -> UpdateManifest:
    """Load/validate manifest structure only (legacy/offline inspection path)."""
    return UpdateManifest.from_dict(_read_manifest_dict(source))


def canonical_manifest_bytes(data: dict[str, Any]) -> bytes:
    """Canonical payload signed by release tooling.

    The detached signature fields themselves are excluded from the payload.
    Stable sorting/separators ensure the same bytes across Python/CI hosts.
    """
    payload = {k: v for k, v in data.items() if k not in {"signature", "signature_algorithm"}}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_manifest_signature(
    data: dict[str, Any], public_key_path: Path | str, *, expected_key_id: str | None = None
) -> None:
    """Verify an Ed25519 signed release manifest; fail closed on any mismatch."""
    signature = data.get("signature")
    algorithm = str(data.get("signature_algorithm", "")).lower()
    key_id = data.get("key_id")
    if algorithm != "ed25519" or not signature or not key_id:
        raise UpdateAgentError("manifest non signé ou signature incomplète")
    if expected_key_id is not None and key_id != expected_key_id:
        raise UpdateAgentError("identifiant de clé de signature inattendu")
    try:
        raw_signature = base64.b64decode(str(signature), validate=True)
    except Exception as exc:
        raise UpdateAgentError("signature du manifeste invalide") from exc
    if len(raw_signature) != 64:
        raise UpdateAgentError("signature Ed25519 de longueur invalide")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        raw_key = Path(public_key_path).read_bytes()
        key = serialization.load_pem_public_key(raw_key)
        if not isinstance(key, Ed25519PublicKey):
            raise UpdateAgentError("la clé publique n'est pas Ed25519")
        key.verify(raw_signature, canonical_manifest_bytes(data))
    except UpdateAgentError:
        raise
    except Exception as exc:
        raise UpdateAgentError("signature du manifeste rejetée") from exc


def load_trusted_manifest(
    source: Path | str, public_key_path: Path | str, *, expected_key_id: str | None = None
) -> UpdateManifest:
    data = _read_manifest_dict(source)
    # Structural validation before expensive crypto gives deterministic errors.
    manifest = UpdateManifest.from_dict(data)
    verify_manifest_signature(data, public_key_path, expected_key_id=expected_key_id)
    return manifest


def compare_versions(a: str, b: str) -> int:
    """Compare dotted numeric versions, ignoring prerelease suffixes after '-'."""
    def parts(v: str):
        core = v.split("-", 1)[0]
        out = []
        for p in core.split("."):
            try:
                out.append(int(p))
            except ValueError:
                out.append(0)
        return tuple((out + [0, 0, 0])[:3])
    pa, pb = parts(a), parts(b)
    return (pa > pb) - (pa < pb)


def is_update_available(current_version: str, manifest: UpdateManifest) -> bool:
    if manifest.min_version and compare_versions(current_version, manifest.min_version) < 0:
        raise UpdateAgentError("version locale trop ancienne pour cette mise à jour")
    return compare_versions(manifest.version, current_version) > 0


def download_verified(
    manifest: UpdateManifest,
    destination: Path,
    *,
    max_bytes: int = 2 * 1024**3,
    timeout: int = 60,
) -> Path:
    if manifest.size_bytes > max_bytes:
        raise UpdateAgentError("artefact trop volumineux")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="sigma-update-", suffix=".part", dir=destination.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        request = urllib.request.Request(manifest.url, headers={"User-Agent": "SIGMA-Update-Agent/4.42"})
        total = 0
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=timeout) as response, tmp.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > manifest.size_bytes or total > max_bytes:
                    raise UpdateAgentError("taille téléchargée supérieure à la limite")
                digest.update(chunk)
                out.write(chunk)
        if total != manifest.size_bytes:
            raise UpdateAgentError("taille de l'artefact inattendue")
        if digest.hexdigest() != manifest.sha256:
            raise UpdateAgentError("vérification SHA-256 échouée")
        os.replace(tmp, destination)
        return destination
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            finally:
                os.close(fd)
            return
        except FileExistsError as exc:
            if attempt == 0:
                try:
                    raw = lock_path.read_text(encoding="ascii").strip()
                    pid = int(raw)
                except (OSError, ValueError):
                    pid = -1
                if pid > 0 and not _pid_is_alive(pid):
                    try:
                        lock_path.unlink()
                        continue
                    except OSError as unlink_exc:
                        logger.debug("Verrou de mise à jour orphelin non supprimé: %s", unlink_exc)
            raise UpdateAgentError("mise à jour déjà en cours") from exc


def release_lock(lock_path: Path):
    lock_path.unlink(missing_ok=True)


def write_state(path: Path, **values: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.time(), **values}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
