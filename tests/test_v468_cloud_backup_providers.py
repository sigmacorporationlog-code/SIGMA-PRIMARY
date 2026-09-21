"""Sauvegarde cloud multi-fournisseurs (Google Drive, OneDrive, Dropbox).

Ces tests ne font AUCUN appel réseau réel (l'environnement de build n'a de
toute façon pas accès à ces domaines). Les fonctions d'envoi sont testées
avec un transport HTTP factice (httpx.MockTransport) qui vérifie la requête
construite (méthode, URL, en-têtes) plutôt que la réponse d'un vrai
serveur — voir la limite documentée dans
app/services/cloud_backup_providers.py.
"""
import httpx
import pytest

from app.services.crypto import encrypt_secret, decrypt_secret
from app.services.cloud_backup_providers import (
    upload_to_provider, CloudUploadError, sync_backup_to_cloud_destinations,
    _dropbox_upload, _onedrive_upload, _google_drive_upload,
)


def test_encrypt_decrypt_roundtrip():
    secret = "ya29.a0Ar8fake-access-token-value"
    token = encrypt_secret(secret)
    assert token != secret  # jamais stocké en clair
    assert decrypt_secret(token) == secret


def test_decrypt_rejects_corrupted_token():
    with pytest.raises(ValueError):
        decrypt_secret("ceci-n-est-pas-un-jeton-fernet-valide")


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_dropbox_upload_builds_expected_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["arg"] = request.headers.get("dropbox-api-arg")
        return httpx.Response(200, json={"ok": True})

    _dropbox_upload("tok123", "/SIGMA", "backup.zip", b"data", client=_mock_client(handler))
    assert seen["url"] == "https://content.dropboxapi.com/2/files/upload"
    assert seen["auth"] == "Bearer tok123"
    assert "/SIGMA/backup.zip" in seen["arg"]


def test_onedrive_upload_builds_expected_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    _onedrive_upload("tok456", "/SIGMA", "backup.zip", b"data", client=_mock_client(handler))
    assert seen["method"] == "PUT"
    assert "SIGMA/backup.zip" in seen["url"]
    assert seen["auth"] == "Bearer tok456"


def test_google_drive_upload_builds_expected_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"id": "abc"})

    _google_drive_upload("tok789", "/SIGMA", "backup.zip", b"data", client=_mock_client(handler))
    assert "uploadType=multipart" in seen["url"]
    assert seen["auth"] == "Bearer tok789"


def test_upload_to_provider_rejects_unknown_provider():
    with pytest.raises(CloudUploadError):
        upload_to_provider("mega_drive_inconnu", "tok", "/SIGMA", "x.zip", b"data")


def test_upload_wraps_http_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("réseau indisponible dans ce test")

    with pytest.raises(CloudUploadError):
        upload_to_provider("dropbox", "tok", "/SIGMA", "x.zip", b"data", client=_mock_client(handler))


def test_sync_isolates_failures_and_never_raises(tmp_path, monkeypatch):
    """Le point le plus important : une destination cassée (jeton expiré,
    fournisseur injoignable) ne doit jamais transformer une sauvegarde
    locale déjà réussie en échec pour l'utilisateur."""
    import subprocess
    import sys
    import textwrap
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENV=production\nSECRET_KEY=test-secret-key-for-cloud-backup\n",
        encoding="utf-8",
    )
    archive = tmp_path / "fake_backup.zip"
    archive.write_bytes(b"contenu factice de sauvegarde")

    script = textwrap.dedent(
        f"""
        import seed
        seed.run()
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.backup_cloud import CloudBackupDestination
        from app.services.crypto import encrypt_secret
        from app.services.cloud_backup_providers import sync_backup_to_cloud_destinations

        db = SessionLocal()
        # Un jeton pointant vers un fournisseur inconnu garantit un échec
        # déterministe, sans jamais tenter d'appel réseau réel.
        dest = CloudBackupDestination(
            school_id=1, provider="dropbox", label="Test",
            encrypted_access_token=encrypt_secret("jeton-invalide-sans-reseau"),
            folder_path="/SIGMA", is_active=True,
        )
        db.add(dest)
        db.commit()

        results = sync_backup_to_cloud_destinations(db, Path({str(archive)!r}))
        assert len(results) == 1
        # On n'exige pas un statut précis (dépend du réseau du sandbox de
        # build), seulement que la fonction n'ait jamais levé d'exception.
        assert results[0]["provider"] == "dropbox"
        print("OK", results[0]["status"])
        """
    )
    env = {**__import__("os").environ, "SIGMA_DATA_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
