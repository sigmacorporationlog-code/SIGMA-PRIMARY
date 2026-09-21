"""Envoi d'une archive de sauvegarde vers un fournisseur cloud externe.

IMPORTANT — limite honnête : ce module appelle les vraies API REST de
chaque fournisseur (endpoints, en-têtes et formats de requête conformes à
leur documentation publique), mais n'a jamais pu être exécuté contre un
compte réel Google/Microsoft/Dropbox dans cet environnement : l'accès
réseau y est restreint à une liste blanche qui n'inclut pas ces domaines,
et aucun jeton de test n'est disponible ici. Chaque fonction est testée
par simulation (transport HTTP factice qui vérifie la requête construite),
pas par un appel réel. Une vérification en conditions réelles, une fois
déployé avec un vrai jeton, reste nécessaire avant de considérer ceci
"prêt pour la production".

Obtenir un jeton aujourd'hui est un geste manuel (coller un jeton d'accès
généré depuis la console développeur du fournisseur) : le flux OAuth
complet (autorisation via navigateur, rafraîchissement automatique des
jetons expirés) n'est pas implémenté dans cette étape.
"""
from __future__ import annotations

import httpx


class CloudUploadError(RuntimeError):
    """Échec d'envoi vers un fournisseur cloud — jamais laissée remonter
    telle quelle à l'appelant de create_backup() : une sauvegarde locale
    réussie ne doit jamais être considérée en échec à cause d'un problème
    réseau ou de jeton expiré côté cloud."""


def _dropbox_upload(access_token: str, folder_path: str, filename: str, content: bytes, client: httpx.Client | None = None) -> None:
    """Dropbox: POST simple, jeton en en-tête, chemin+métadonnées en JSON
    dans l'en-tête Dropbox-API-Arg (voir /2/files/upload dans leur doc)."""
    import json

    path = f"{folder_path.rstrip('/')}/{filename}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Dropbox-API-Arg": json.dumps({"path": path, "mode": "overwrite", "mute": True}),
        "Content-Type": "application/octet-stream",
    }
    http = client or httpx.Client(timeout=60)
    try:
        resp = http.post("https://content.dropboxapi.com/2/files/upload", headers=headers, content=content)
        if resp.status_code >= 400:
            raise CloudUploadError(f"Dropbox a refusé l'envoi ({resp.status_code}): {resp.text[:300]}")
    finally:
        if client is None:
            http.close()


def _onedrive_upload(access_token: str, folder_path: str, filename: str, content: bytes, client: httpx.Client | None = None) -> None:
    """OneDrive (Microsoft Graph): PUT direct pour les fichiers < 4 Mo
    (une sauvegarde SIGMA dépasse rarement cette taille ; pour les grosses
    archives, Microsoft recommande une session d'upload par segments —
    non implémentée ici, à ajouter si des écoles ont de très gros volumes
    de médias)."""
    path = f"{folder_path.strip('/')}/{filename}"
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{path}:/content"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
    http = client or httpx.Client(timeout=60)
    try:
        resp = http.put(url, headers=headers, content=content)
        if resp.status_code >= 400:
            raise CloudUploadError(f"OneDrive a refusé l'envoi ({resp.status_code}): {resp.text[:300]}")
    finally:
        if client is None:
            http.close()


def _google_drive_upload(access_token: str, folder_path: str, filename: str, content: bytes, client: httpx.Client | None = None) -> None:
    """Google Drive: upload multipart simple (métadonnées + contenu en un
    seul appel — suffisant pour des archives de sauvegarde de taille
    modeste). folder_path n'est pas résolu en ID de dossier Drive ici : le
    fichier est déposé à la racine avec le nom de fichier complet ; un
    classement par dossier est une amélioration possible ultérieure."""
    metadata = {"name": filename}
    files = {
        "metadata": (None, __import__("json").dumps(metadata), "application/json; charset=UTF-8"),
        "file": (filename, content, "application/octet-stream"),
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    http = client or httpx.Client(timeout=60)
    try:
        resp = http.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=headers, files=files,
        )
        if resp.status_code >= 400:
            raise CloudUploadError(f"Google Drive a refusé l'envoi ({resp.status_code}): {resp.text[:300]}")
    finally:
        if client is None:
            http.close()


_UPLOADERS = {
    "dropbox": _dropbox_upload,
    "onedrive": _onedrive_upload,
    "google_drive": _google_drive_upload,
}


def upload_to_provider(provider: str, access_token: str, folder_path: str, filename: str, content: bytes, client: httpx.Client | None = None) -> None:
    fn = _UPLOADERS.get(provider)
    if fn is None:
        raise CloudUploadError(f"Fournisseur cloud non supporté: {provider}")
    try:
        fn(access_token, folder_path, filename, content, client=client)
    except httpx.HTTPError as exc:
        raise CloudUploadError(f"Erreur réseau vers {provider}: {exc}") from exc


def sync_backup_to_cloud_destinations(db, archive_path) -> list[dict]:
    """Pousse une archive de sauvegarde locale vers toutes les destinations
    cloud actives. Ne lève jamais : une destination en échec (jeton expiré,
    réseau coupé...) est journalisée sur cette destination et n'affecte pas
    les autres, et surtout ne remet jamais en cause la sauvegarde locale
    déjà réalisée avec succès — c'est elle qui reste la garantie principale.

    L'archive est poussée vers TOUTES les destinations actives de
    l'installation (indépendamment de school_id) : une installation SIGMA
    ne produit qu'une seule archive globale par sauvegarde, quel que soit
    le nombre d'établissements qu'elle héberge.
    """
    from datetime import datetime, timezone
    from app.models.backup_cloud import CloudBackupDestination
    from app.services.crypto import decrypt_secret

    results = []
    destinations = db.query(CloudBackupDestination).filter(CloudBackupDestination.is_active.is_(True)).all()
    if not destinations:
        return results
    content = archive_path.read_bytes()
    filename = archive_path.name
    for dest in destinations:
        try:
            token = decrypt_secret(dest.encrypted_access_token)
            upload_to_provider(dest.provider, token, dest.folder_path, filename, content)
        except Exception as exc:  # noqa: BLE001 — on isole volontairement toute erreur par destination
            dest.last_sync_error = str(exc)[:500]
            results.append({"destination_id": dest.id, "provider": dest.provider, "status": "error", "error": str(exc)})
        else:
            dest.last_synced_at = datetime.now(timezone.utc)
            dest.last_sync_error = None
            results.append({"destination_id": dest.id, "provider": dest.provider, "status": "ok"})
    db.commit()
    return results
