"""Sauvegarde locale robuste de SIGMA.

Les sauvegardes sont des ZIP atomiques contenant la base SQLite, les médias
et un manifeste d'intégrité SHA-256. La restauration automatique n'est pas
exécutée par l'API : une archive doit d'abord être validée explicitement.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePosixPath
import hashlib
import json
import logging

logger = logging.getLogger(__name__)
import os
import shutil
import sqlite3
import tempfile
import zipfile
import uuid

from app.core.config import settings
from app.core.database import engine, is_sqlite
from app.core.paths import data_dir
from app.services.media import media_root


def backup_root() -> Path:
    root = data_dir() / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sqlite_backup(target: Path) -> None:
    if not is_sqlite:
        raise RuntimeError("La sauvegarde intégrée cible SQLite.")
    db_path = Path(engine.url.database or "")
    if not db_path.exists():
        raise FileNotFoundError("Base SIGMA introuvable")
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
        dst.execute("PRAGMA integrity_check")
        result = dst.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("La copie SQLite échoue au contrôle d'intégrité")
    finally:
        dst.close()
        src.close()


def create_backup() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    final = backup_root() / f"SIGMA_backup_{stamp}.zip"
    temp_final = backup_root() / f".SIGMA_backup_{stamp}.tmp.zip"
    with tempfile.TemporaryDirectory(prefix="sigma_backup_") as tmp:
        tmp_path = Path(tmp)
        db_copy = tmp_path / "sigma.db"
        _sqlite_backup(db_copy)
        files: list[tuple[Path, str]] = [(db_copy, "sigma.db")]
        root = media_root()
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    files.append((path, str(Path("media") / path.relative_to(root))))
        manifest = {
            "format": 2,
            "app_version": settings.APP_VERSION,
            "created_at": datetime.now().isoformat(),
            "files": [{"path": arc, "sha256": _sha256(src), "size": src.stat().st_size} for src, arc in files],
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            with zipfile.ZipFile(temp_final, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for src, arc in files:
                    zf.write(src, arc)
                zf.write(manifest_path, "manifest.json")
            validate_backup(temp_final)
            os.replace(temp_final, final)
        finally:
            if temp_final.exists():
                temp_final.unlink()
    prune_backups()
    return final


def validate_backup(path: Path) -> dict:
    """Valide intégrité, confinement et limites d'une archive SIGMA."""
    path = Path(path)
    if not path.exists() or path.suffix.lower() != ".zip":
        raise ValueError("Archive SIGMA invalide")
    if path.stat().st_size > settings.BACKUP_MAX_ARCHIVE_BYTES:
        raise ValueError("Archive de sauvegarde trop volumineuse")
    with zipfile.ZipFile(path, "r") as zf:
        if zf.testzip() is not None:
            raise ValueError("Archive ZIP corrompue")
        infos = zf.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError("Archive ZIP contenant des entrées dupliquées")
        if "manifest.json" not in names:
            raise ValueError("Manifeste de sauvegarde absent")
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except Exception as exc:
            raise ValueError("Manifeste de sauvegarde invalide") from exc
        if manifest.get("format") != 2:
            raise ValueError("Version de format de sauvegarde non supportée")
        items = manifest.get("files")
        if not isinstance(items, list) or not items:
            raise ValueError("Manifeste de sauvegarde vide")
        declared = []
        total = 0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Entrée de manifeste invalide")
            name = item.get("path")
            if not isinstance(name, str) or not name or name == "manifest.json":
                raise ValueError(f"Chemin de sauvegarde invalide: {name}")
            if name in declared:
                raise ValueError(f"Chemin de sauvegarde dupliqué: {name}")
            declared.append(name)
            posix = PurePosixPath(name)
            if posix.is_absolute() or ".." in posix.parts or "\\" in name:
                raise ValueError(f"Chemin de sauvegarde dangereux: {name}")
            if name not in names:
                raise ValueError(f"Fichier de sauvegarde absent: {name}")
            info = zf.getinfo(name)
            if info.is_dir() or info.file_size > settings.BACKUP_MAX_FILE_BYTES:
                raise ValueError(f"Fichier de sauvegarde trop volumineux: {name}")
            expected_size = item.get("size")
            if not isinstance(expected_size, int) or expected_size < 0 or info.file_size != expected_size:
                raise ValueError(f"Taille incohérente: {name}")
            expected_hash = item.get("sha256")
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                raise ValueError(f"Empreinte SHA-256 invalide: {name}")
            total += info.file_size
            if total > settings.BACKUP_MAX_TOTAL_BYTES:
                raise ValueError("Taille totale de sauvegarde dépassée")
            digest = hashlib.sha256(zf.read(name)).hexdigest()
            if digest != expected_hash:
                raise ValueError(f"Empreinte SHA-256 incohérente: {name}")
        expected_names = set(declared) | {"manifest.json"}
        if set(names) != expected_names:
            extras = sorted(set(names) - expected_names)
            raise ValueError(f"Entrées non déclarées dans le manifeste: {extras[0] if extras else 'inconnue'}")
        if "sigma.db" not in declared:
            raise ValueError("Base SQLite absente")
        # Vérification réelle de la base avant qu'une archive puisse être
        # considérée comme restaurable. Le fichier reste en mémoire/temporaire.
        db_bytes = zf.read("sigma.db")
        # delete=False + fermeture explicite avant sqlite3.connect(): sur Windows,
        # un fichier ouvert par NamedTemporaryFile(delete=True) est verrouillé et
        # un second handle (ici sqlite3) ne peut pas l'ouvrir, d'où
        # "unable to open database file". On ferme le handle Python avant de
        # laisser sqlite3 ouvrir le fichier, puis on nettoie nous-mêmes.
        tmp = tempfile.NamedTemporaryFile(prefix="sigma_validate_", suffix=".db", delete=False)
        tmp_path = tmp.name
        try:
            tmp.write(db_bytes)
            tmp.flush()
            tmp.close()
            con = sqlite3.connect(tmp_path)
            try:
                try:
                    result = con.execute("PRAGMA integrity_check").fetchone()
                except sqlite3.DatabaseError as exc:
                    raise ValueError("Base SQLite de sauvegarde invalide") from exc
                if not result or result[0] != "ok":
                    raise ValueError("Base SQLite de sauvegarde invalide")
            finally:
                con.close()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                logger.debug("Fichier temporaire de validation déjà supprimé ou inaccessible: %s", exc)
        return manifest


def list_backups() -> list[dict]:
    rows = []
    for p in sorted(backup_root().glob("SIGMA_backup_*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            manifest = validate_backup(p)
            rows.append({"name": p.name, "size": p.stat().st_size, "created_at": manifest["created_at"], "valid": True})
        except (OSError, ValueError, zipfile.BadZipFile):
            rows.append({"name": p.name, "size": p.stat().st_size, "created_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(), "valid": False})
    return rows



def prune_backups(max_keep: int | None = None) -> dict:
    """Supprime uniquement les anciennes sauvegardes valides, jamais la plus récente."""
    limit = max_keep if max_keep is not None else settings.MAX_BACKUPS_TO_KEEP
    limit = max(1, int(limit))
    candidates = sorted(backup_root().glob("SIGMA_backup_*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
    removed = []
    kept = 0
    for path in candidates:
        try:
            validate_backup(path)
            if kept < limit:
                kept += 1
                continue
            path.unlink(missing_ok=True)
            removed.append(path.name)
        except (OSError, ValueError, zipfile.BadZipFile):
            # Une archive invalide n'est pas supprimée automatiquement : elle
            # doit rester visible pour diagnostic et intervention manuelle.
            continue
    return {"max_keep": limit, "kept": kept, "removed": removed, "removed_count": len(removed)}

def restore_backup_to_directory(archive: Path, target_dir: Path) -> dict:
    """Restaure une sauvegarde validée dans un dossier isolé.

    Cette primitive ne touche jamais au DATA_DIR courant. Elle est destinée
    aux restaurations contrôlées, aux tests de reprise et à la préparation
    d'une future procédure de restauration administrateur.
    """
    archive = Path(archive)
    target_dir = Path(target_dir)
    manifest = validate_backup(archive)
    target_dir.mkdir(parents=True, exist_ok=True)

    staging = Path(tempfile.mkdtemp(prefix="sigma_restore_", dir=str(target_dir.parent)))
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            root = staging.resolve()
            for item in manifest["files"]:
                name = item["path"]
                destination = (staging / name).resolve()
                if destination != root and root not in destination.parents:
                    raise ValueError(f"Chemin de restauration dangereux: {name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name, "r") as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

        db_copy = staging / "sigma.db"
        connection = sqlite3.connect(str(db_copy))
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValueError("Base restaurée invalide")
        finally:
            connection.close()

        restored_manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8")) if (staging / "manifest.json").exists() else manifest
        if target_dir.exists():
            # La cible doit être vide pour éviter une restauration partielle.
            if any(target_dir.iterdir()):
                raise ValueError("Le dossier cible de restauration doit être vide")
        target_dir.mkdir(parents=True, exist_ok=True)
        for child in staging.iterdir():
            shutil.move(str(child), str(target_dir / child.name))
        return {
            "status": "restored",
            "target": str(target_dir),
            "files": len(manifest["files"]),
            "app_version": restored_manifest.get("app_version"),
        }
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


RESTORE_STATE_FILE = "restore_pending.json"


def restore_state_path() -> Path:
    return data_dir() / RESTORE_STATE_FILE


def prepare_restore(archive: Path) -> dict:
    """Prépare une restauration administrateur pour le prochain redémarrage.

    La base et les médias de production ne sont pas modifiés pendant cette
    opération. Une sauvegarde de sécurité est créée avant de placer l'archive
    dans la zone de staging. L'application appliquera le plan au démarrage.
    """
    archive = Path(archive)
    manifest = validate_backup(archive)
    state = restore_state_path()
    if state.exists():
        raise RuntimeError("Une restauration est déjà en attente")

    safety_backup = create_backup()
    restore_root = data_dir() / "restore_staging"
    restore_root.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staged = restore_root / f"restore_{token}.zip"
    shutil.copy2(archive, staged)
    plan = {
        "token": token,
        "archive": str(staged),
        "safety_backup": str(safety_backup),
        "created_at": datetime.now().isoformat(),
        "app_version": manifest.get("app_version"),
        "status": "pending_restart",
    }
    state.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def get_restore_state() -> dict | None:
    path = restore_state_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("État de restauration illisible") from exc


def cancel_restore() -> dict:
    state = get_restore_state()
    if not state:
        return {"status": "none"}
    archive = Path(state.get("archive", ""))
    restore_state_path().unlink(missing_ok=True)
    if archive.exists():
        archive.unlink()
    return {"status": "cancelled", "token": state.get("token")}


def _preserve_and_validate_commercial_state(restored_db: Path) -> dict:
    """Preserve the live subscription state across restore and validate quotas.

    Customer backups must never be able to roll back a licence/trial or raise
    plan limits. The live control-plane table is therefore copied into the
    staged database before it can replace the production database.
    """
    live_db = Path(engine.url.database or "")
    if not live_db.exists():
        raise RuntimeError("Base SQLite courante introuvable pour protéger la licence")
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect(str(restored_db))
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "school_subscriptions" not in tables:
            raise ValueError("Archive incompatible: table des abonnements absente")
        conn.execute("ATTACH DATABASE ? AS live_db", (str(live_db),))
        live_tables = {row[0] for row in conn.execute("SELECT name FROM live_db.sqlite_master WHERE type='table'").fetchall()}
        if "school_subscriptions" not in live_tables:
            raise RuntimeError("Base courante incompatible: table des abonnements absente")
        live_rows = conn.execute("SELECT * FROM live_db.school_subscriptions ORDER BY id").fetchall()
        if not live_rows:
            raise RuntimeError("Aucun état de licence courant à préserver")
        columns = [row[1] for row in conn.execute("PRAGMA table_info(school_subscriptions)").fetchall()]
        live_columns = [row[1] for row in conn.execute("PRAGMA live_db.table_info(school_subscriptions)").fetchall()]
        if columns != live_columns:
            raise ValueError("Archive incompatible: schéma des abonnements différent")
        placeholders = ",".join("?" for _ in columns)
        conn.execute("DELETE FROM school_subscriptions")
        conn.executemany(f"INSERT INTO school_subscriptions ({','.join(columns)}) VALUES ({placeholders})", live_rows)

        violations = []
        for school_id, max_users, max_students, status, ends_on in conn.execute(
            "SELECT school_id, max_users, max_students, status, ends_on FROM school_subscriptions"
        ).fetchall():
            if status not in {"trial", "active"} or (ends_on and ends_on < today):
                continue
            users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE school_id=? AND is_active=1", (school_id,)
            ).fetchone()[0]
            students = conn.execute(
                "SELECT COUNT(*) FROM students WHERE school_id=? AND status='active'", (school_id,)
            ).fetchone()[0]
            if users > max_users or students > max_students:
                violations.append({
                    "school_id": school_id, "users": users, "max_users": max_users,
                    "students": students, "max_students": max_students,
                })
        if violations:
            raise ValueError(f"Archive refusée: dépassement de quota commercial détecté: {violations}")
        conn.commit()
        return {"subscriptions_preserved": len(live_rows), "quota_violations": 0}
    finally:
        try:
            conn.execute("DETACH DATABASE live_db")
        except sqlite3.Error as exc:
            logger.debug("DETACH DATABASE live_db non nécessaire ou déjà détaché: %s", exc)
        conn.close()


def apply_pending_restore() -> dict | None:
    """Applique un plan de restauration au démarrage, avant d'accepter des requêtes."""
    state = get_restore_state()
    if not state:
        return None
    archive = Path(state.get("archive", ""))
    if not archive.exists():
        raise RuntimeError("Archive de restauration en attente introuvable")
    validate_backup(archive)

    root = data_dir()
    staging = Path(tempfile.mkdtemp(prefix="sigma_restore_apply_", dir=str(root)))
    old_db = root / f".sigma.db.rollback.{state['token']}"
    old_media = root / f".media.rollback.{state['token']}"
    new_db = staging / "sigma.db"
    new_media = staging / "media"
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            manifest = validate_backup(archive)
            safe_root = staging.resolve()
            for item in manifest["files"]:
                name = item["path"]
                destination = (staging / name).resolve()
                if destination != safe_root and safe_root not in destination.parents:
                    raise ValueError(f"Chemin de restauration dangereux: {name}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name, "r") as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

        commercial_guard = _preserve_and_validate_commercial_state(new_db)
        connection = sqlite3.connect(str(new_db))
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValueError("Base restaurée invalide")
        finally:
            connection.close()

        live_db = Path(engine.url.database or "")
        if not live_db:
            raise RuntimeError("Chemin SQLite de production introuvable")
        live_db.parent.mkdir(parents=True, exist_ok=True)
        if live_db.exists():
            os.replace(live_db, old_db)
        os.replace(new_db, live_db)

        live_media = media_root()
        if live_media.exists():
            os.replace(live_media, old_media)
        if new_media.exists():
            os.replace(new_media, live_media)
        else:
            live_media.mkdir(parents=True, exist_ok=True)

        state["status"] = "applied"
        state["applied_at"] = datetime.now().isoformat()
        restore_state_path().unlink(missing_ok=True)
        if old_db.exists(): old_db.unlink()
        if old_media.exists(): shutil.rmtree(old_media, ignore_errors=True)
        archive.unlink(missing_ok=True)
        state["commercial_guard"] = commercial_guard
        return state
    except Exception:
        if new_db.exists():
            new_db.unlink()
        live_db = Path(engine.url.database or "")
        if old_db.exists():
            if live_db.exists(): live_db.unlink()
            os.replace(old_db, live_db)
        live_media = media_root()
        if old_media.exists():
            if live_media.exists(): shutil.rmtree(live_media, ignore_errors=True)
            os.replace(old_media, live_media)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
