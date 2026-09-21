"""Moteur de mise à jour contrôlée des postes clients SIGMA.

Le moteur n'exécute jamais un programme téléchargé. Il accepte uniquement un
manifest JSON local/HTTPS, vérifie le SHA-256 du paquet, sauvegarde la
configuration locale, installe dans un répertoire temporaire puis remplace
atomiquement les fichiers applicatifs. En cas d'échec, le précédent arbre
applicatif est restauré.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import ssl
import tempfile
import urllib.request
import uuid
import stat

from app.services.compatibility import parse_version


class UpdateError(RuntimeError):
    """Erreur explicite du pipeline de mise à jour client."""


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    package_sha256: str
    package_size: int
    package_url: str

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateManifest":
        required = {"version", "package_sha256", "package_size", "package_url"}
        if not required.issubset(data):
            raise UpdateError("Manifest incomplet")
        version = str(data["version"])
        parse_version(version)
        sha = str(data["package_sha256"]).lower()
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise UpdateError("SHA-256 invalide")
        size = int(data["package_size"])
        if size <= 0:
            raise UpdateError("Taille de paquet invalide")
        url = str(data["package_url"])
        if not (url.startswith("https://") or url.startswith("file://")):
            raise UpdateError("Seuls HTTPS et file:// sont autorisés")
        return cls(version, sha, size, url)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> UpdateManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Manifest illisible: {exc}") from exc
    return UpdateManifest.from_dict(data)


def _download(url: str, destination: Path, expected_size: int) -> None:
    if url.startswith("file://"):
        source = Path(urllib.request.url2pathname(url[7:])).resolve()
        if not source.is_file():
            raise UpdateError("Paquet local introuvable")
        shutil.copyfile(source, destination)
    else:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "SIGMA-Updater/2"})
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response, destination.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
    if destination.stat().st_size != expected_size:
        destination.unlink(missing_ok=True)
        raise UpdateError("Taille du paquet différente du manifest")


def _safe_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def update_client(*, current_version: str, manifest_path: Path, install_dir: Path, backup_root: Path) -> dict:
    """Télécharge/vérifie/installe une version et restaure l'ancienne en cas d'échec."""
    manifest = load_manifest(manifest_path)
    current = parse_version(current_version)
    target = parse_version(manifest.version)
    if target <= current:
        return {"status": "up_to_date", "current_version": current_version, "target_version": manifest.version}
    if target.major != current.major:
        raise UpdateError("Mise à jour majeure refusée automatiquement")

    install_dir = install_dir.resolve()
    backup_root = backup_root.resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    install_dir.parent.mkdir(parents=True, exist_ok=True)

    token = uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="sigma_client_update_", dir=str(backup_root.parent)) as tmp:
        tmpdir = Path(tmp)
        package = tmpdir / "package.bin"
        _download(manifest.package_url, package, manifest.package_size)
        actual = sha256_file(package)
        if actual != manifest.package_sha256:
            raise UpdateError("SHA-256 du paquet incorrect")

        # Le paquet est attendu comme une archive ZIP applicative SIGMA.
        import zipfile
        with zipfile.ZipFile(package) as zf:
            bad = zf.testzip()
            if bad:
                raise UpdateError(f"Archive corrompue: {bad}")
            members = [m for m in zf.infolist() if m.filename]
            if not members:
                raise UpdateError("Archive vide")
            root_names = {m.filename.replace("\\", "/").split("/", 1)[0] for m in members}
            if len(root_names) != 1 or "" in root_names or "." in root_names or ".." in root_names:
                raise UpdateError("Archive client non normalisée")
            uncompressed_total = sum(max(0, int(m.file_size)) for m in members)
            if uncompressed_total > max(16 * 1024 * 1024, manifest.package_size * 20):
                raise UpdateError("Archive client trop volumineuse après décompression")
            extracted = tmpdir / "new"
            extracted.mkdir()
            root = extracted.resolve()
            for info in members:
                normalized = info.filename.replace("\\", "/")
                target = (extracted / normalized).resolve()
                if target != root and root not in target.parents:
                    raise UpdateError(f"Chemin ZIP dangereux: {info.filename}")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK or mode == stat.S_IFCHR or mode == stat.S_IFBLK or mode == stat.S_IFIFO:
                    raise UpdateError(f"Type de fichier ZIP interdit: {info.filename}")
                if normalized.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
            roots = [p for p in extracted.iterdir()]
            if len(roots) != 1 or not roots[0].is_dir():
                raise UpdateError("Racine du paquet invalide")
            new_tree = roots[0]

        backup_dir = backup_root / f"client-{token}"
        if install_dir.exists():
            _safe_copy_tree(install_dir, backup_dir)
        else:
            backup_dir.mkdir(parents=True)

        previous = install_dir.parent / f".{install_dir.name}.previous-{token}"
        try:
            if install_dir.exists():
                os.replace(install_dir, previous)
            os.replace(new_tree, install_dir)
            if previous.exists():
                shutil.rmtree(previous)
        except Exception as exc:
            try:
                if install_dir.exists():
                    shutil.rmtree(install_dir)
                if previous.exists():
                    os.replace(previous, install_dir)
                elif backup_dir.exists() and any(backup_dir.iterdir()):
                    _safe_copy_tree(backup_dir, install_dir)
            except Exception as rollback_exc:
                raise UpdateError(f"Installation échouée et rollback impossible: {rollback_exc}") from exc
            raise UpdateError(f"Installation échouée; rollback effectué: {exc}") from exc

        # La sauvegarde reste disponible pour audit/retour manuel.
        marker = backup_dir / "update.json"
        marker.write_text(json.dumps({
            "status": "installed", "from_version": current_version,
            "to_version": manifest.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "sha256": actual,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "updated", "from_version": current_version, "to_version": manifest.version,
                "backup_dir": str(backup_dir), "sha256": actual}
