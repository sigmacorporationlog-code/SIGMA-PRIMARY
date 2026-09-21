"""Client HTTP de synchronisation SIGMA Primaire 2.8.

Ce module orchestre le stockage offline (SQLite local) avec l'API /api/sync.
Il ne dépend pas de requests: urllib de la bibliothèque standard suffit pour
un poste client Windows même lorsque le réseau est indisponible.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from app.services.offline_client import OfflineSyncStore
from app.core.config import settings


class SyncNetworkError(RuntimeError):
    """Erreur réseau temporaire: les données locales restent intactes."""


class SyncRemoteError(RuntimeError):
    """Erreur HTTP/API non récupérable automatiquement."""


@dataclass(frozen=True)
class SyncResult:
    status: str
    pushed: int = 0
    applied: int = 0
    conflicts: int = 0
    pulled: int = 0
    acked: int = 0
    inbox_applied: int = 0
    error: str | None = None


class JsonHttpTransport:
    """Transport HTTP minimal et testable."""

    def __init__(self, base_url: str, token_provider: Callable[[], str | None], timeout: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.timeout = timeout

    def request(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        url = self.base_url + path
        headers = {"Accept": "application/json"}
        token = self.token_provider()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SyncRemoteError(f"HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SyncNetworkError(str(exc)) from exc


class LocalReadModel:
    """Cache locale générique pour permettre la consultation après déconnexion."""

    TABLES = {
        "student": "local_students",
        "guardian": "local_guardians",
        "student_guardian": "local_student_guardians",
        "class_membership": "local_class_memberships",
        "grade": "local_grades",
        "evaluation_result": "local_evaluation_results",
    }

    def __init__(self, store: OfflineSyncStore):
        self.store = store
        self._init()

    def _init(self):
        with self.store._lock, self.store._connect() as db:
            for table in self.TABLES.values():
                db.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
                    entity_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )""")

    def apply(self, item: dict[str, Any]) -> None:
        entity_type = item["entity_type"]
        table = self.TABLES.get(entity_type)
        if table is None:
            return
        entity_id = str(item.get("server_entity_id") or item["entity_id"])
        operation_type = item["operation_type"]
        payload = dict(item.get("payload") or {})
        payload.setdefault("entity_id", entity_id)
        if item.get("server_entity_id") is not None:
            payload["server_entity_id"] = int(item["server_entity_id"])
            payload["client_entity_id"] = str(item["entity_id"])
        incoming_version = int(item.get("server_version") or 0)
        now = datetime.now(timezone.utc).isoformat()
        with self.store._lock, self.store._connect() as db:
            existing = db.execute(f"SELECT payload_json,version,deleted FROM {table} WHERE entity_id=?", (entity_id,)).fetchone()
            current = json.loads(existing[0]) if existing else {}
            current_version = int(existing[1]) if existing else 0
            # Une mutation ancienne ne doit jamais écraser une version plus récente.
            if existing and incoming_version < current_version:
                return
            deleted = 1 if operation_type == "delete" else 0
            if operation_type != "delete":
                current.update(payload)
            db.execute(
                f"""INSERT INTO {table}(entity_id,payload_json,version,deleted,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(entity_id) DO UPDATE SET payload_json=excluded.payload_json,
                    version=excluded.version, deleted=excluded.deleted, updated_at=excluded.updated_at""",
                (entity_id, json.dumps(current, ensure_ascii=False), incoming_version, deleted, now),
            )
            if item.get("server_entity_id") is not None and item.get("entity_id") != str(item["server_entity_id"]):
                # Conserve aussi l'identité pour le poste local.
                db.execute(
                    "INSERT OR REPLACE INTO sync_identity(entity_type,client_entity_id,server_entity_id) VALUES(?,?,?)",
                    (entity_type, str(item["entity_id"]), int(item["server_entity_id"])),
                )

    def get(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        table = self.TABLES.get(entity_type)
        if table is None:
            return None
        with self.store._connect() as db:
            row = db.execute(f"SELECT * FROM {table} WHERE entity_id=?", (str(entity_id),)).fetchone()
        if not row or row["deleted"]:
            return None
        return {
            "entity_id": row["entity_id"],
            "payload": json.loads(row["payload_json"]),
            "version": row["version"],
        }


class SyncClientEngine:
    """Orchestrateur push → apply → pull → cache locale → ACK."""

    def __init__(self, store: OfflineSyncStore, transport: Any, app_version: str | None = None):
        self.store = store
        self.transport = transport
        self.app_version = app_version or settings.APP_VERSION
        self.cache = LocalReadModel(store)

    def check_compatibility(self) -> dict[str, Any]:
        """Vérifie la compatibilité avant toute synchronisation métier."""
        return self.transport.request("GET", "/api/sync/compatibility?" + urllib.parse.urlencode({"client_version": self.app_version}))

    def register(self, name: str, device_type: str = "client") -> dict[str, Any]:
        return self.transport.request("POST", "/api/sync/devices/register", {
            "device_id": self.store.device_id,
            "name": name,
            "device_type": device_type,
            "app_version": self.app_version,
        })

    def heartbeat(self) -> dict[str, Any]:
        return self.transport.request("POST", "/api/sync/devices/heartbeat", {
            "device_id": self.store.device_id,
            "name": self.store.device_id,
            "device_type": "client",
            "app_version": self.app_version,
        })

    def _push(self) -> tuple[int, int, int]:
        pending = self.store.pending(500)
        if not pending:
            return 0, 0, 0
        payload = [{k: item[k] for k in (
            "operation_id", "device_id", "entity_type", "entity_id", "operation_type", "base_version", "payload"
        )} for item in pending]
        response = self.transport.request("POST", "/api/sync/push", payload)
        conflicts = 0
        accepted_ids: list[str] = []
        for item in response.get("items", []):
            op_id = item["operation_id"]
            status = item.get("status")
            if status == "conflict":
                self.store.mark_result(op_id, "conflict", item.get("server_version"), item.get("error"))
                conflicts += 1
            elif status in {"pending", "applied"}:
                accepted_ids.append(op_id)
            else:
                self.store.mark_result(op_id, "failed", item.get("server_version"), item.get("error"))
        applied = 0
        if accepted_ids:
            batch = self.transport.request("POST", "/api/sync/apply-batch", accepted_ids)
            for item in batch.get("items", []):
                op_id = item["operation_id"]
                if item.get("status") == "applied":
                    self.store.mark_result(op_id, "applied", item.get("server_version"))
                    applied += 1
                    mutation = item.get("mutation") or {}
                    if mutation.get("operation_type") == "create" and mutation.get("entity_id") is not None:
                        local = next((x for x in pending if x["operation_id"] == op_id), None)
                        if local:
                            self.store.set_identity(local["entity_type"], local["entity_id"], int(mutation["entity_id"]))
                else:
                    if item.get("http_status") == 409:
                        self.store.mark_result(op_id, "conflict", item.get("server_version"), item.get("error"))
                        conflicts += 1
                    else:
                        self.store.mark_result(op_id, "retry" if item.get("http_status", 0) >= 500 else "failed", item.get("server_version"), item.get("error"))
        return len(pending), applied, conflicts

    def _pull(self) -> tuple[int, int]:
        response = self.transport.request(
            "GET", "/api/sync/pull?" + urllib.parse.urlencode({
                "device_id": self.store.device_id,
                "since_id": self.store.last_pull_id(),
                "limit": 500,
            })
        )
        items = response.get("items", [])
        received = self.store.ingest_pull(items, response.get("next_id"))
        applied = 0
        ack_ids: list[str] = []
        for item in self.store.inbox(500):
            self.cache.apply(item)
            if item.get("server_entity_id") is not None:
                self.store.set_identity(item["entity_type"], str(item["entity_id"]), int(item["server_entity_id"]))
            self.store.mark_inbox_applied(item["operation_id"])
            ack_ids.append(item["operation_id"])
            applied += 1
        if ack_ids:
            ack = self.transport.request("POST", "/api/sync/ack", {
                "device_id": self.store.device_id,
                "operation_ids": ack_ids,
            })
            return received, int(ack.get("acknowledged", 0))
        return received, 0

    def resolve_conflict_remote(self, operation_id: str, resolution: str) -> dict[str, Any]:
        """Résout le conflit côté serveur et aligne la base locale si rebase est choisi."""
        if resolution not in {"discard", "rebase"}:
            raise ValueError("resolution doit être 'discard' ou 'rebase'")
        response = self.transport.request("POST", f"/api/sync/conflicts/{operation_id}/resolve", {"resolution": resolution})
        if resolution == "rebase":
            base_version = response.get("base_version")
            with self.store._lock, self.store._connect() as db:
                db.execute("UPDATE sync_outbox SET base_version=?, status='pending', error=NULL WHERE operation_id=?", (int(base_version or 0), operation_id))
                db.execute("UPDATE sync_conflicts SET resolution='rebase', resolved_at=? WHERE operation_id=?", (datetime.now(timezone.utc).isoformat(), operation_id))
        else:
            with self.store._lock, self.store._connect() as db:
                db.execute("UPDATE sync_conflicts SET resolution='discard', resolved_at=? WHERE operation_id=?", (datetime.now(timezone.utc).isoformat(), operation_id))
        return response

    def sync_once(self) -> SyncResult:
        """Effectue une passe après contrôle de compatibilité."""
        try:
            compat = self.check_compatibility()
            if not compat.get("compatible", False):
                error = compat.get("reason", "Version incompatible")
                self.store.set_sync_state("incompatible", error)
                return SyncResult(status="incompatible", error=error)
            pushed, applied, push_conflicts = self._push()
            pulled, acked = self._pull()
            conflicts = self.store.summary()["unresolved_conflicts"]
            status = "conflict" if conflicts else "synchronized" if not self.store.pending() else "pending"
            error = None if status != "conflict" else "Des conflits de synchronisation nécessitent une résolution"
            self.store.set_sync_state(status, error)
            return SyncResult(status=status, pushed=pushed, applied=applied,
                              conflicts=conflicts, pulled=pulled, acked=acked,
                              inbox_applied=acked, error=error)
        except SyncNetworkError as exc:
            summary = self.store.summary()
            self.store.set_sync_state("offline", str(exc))
            return SyncResult(status="offline", conflicts=summary["unresolved_conflicts"], error=str(exc))
        except SyncRemoteError as exc:
            self.store.set_sync_state("error", str(exc))
            return SyncResult(status="error", conflicts=self.store.summary()["unresolved_conflicts"], error=str(exc))
