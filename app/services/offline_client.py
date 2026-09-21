"""Moteur local de synchronisation offline SIGMA.

Le moteur est volontairement indépendant de SQLAlchemy et utilise SQLite de la
bibliothèque standard afin de fonctionner sur un poste client sans dépendance
réseau ni serveur local. Il conserve durablement la file sortante, les
livraisons reçues et les conflits jusqu'à leur traitement.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OfflineSyncStore:
    """File offline persistante d'un poste SIGMA.

    Une instance représente un poste et un établissement. Les opérations sont
    idempotentes grâce à ``operation_id`` et les écritures sont protégées par
    une transaction SQLite.
    """

    def __init__(self, path: str | Path, device_id: str, school_id: int):
        self.path = str(path)
        self.device_id = device_id
        self.school_id = int(school_id)
        self._lock = threading.RLock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_outbox (
                operation_id TEXT PRIMARY KEY,
                school_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                base_version INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                server_version INTEGER,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_sync_outbox_status_id
                ON sync_outbox(status, created_at);
            CREATE TABLE IF NOT EXISTS sync_inbox (
                operation_id TEXT PRIMARY KEY,
                server_id INTEGER,
                source_device_id TEXT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                server_version INTEGER,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'received',
                received_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                operation_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                base_version INTEGER NOT NULL,
                server_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                error TEXT,
                resolution TEXT,
                resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sync_identity (
                entity_type TEXT NOT NULL,
                client_entity_id TEXT NOT NULL,
                server_entity_id INTEGER NOT NULL,
                PRIMARY KEY(entity_type, client_entity_id),
                UNIQUE(entity_type, server_entity_id)
            );
            """)
            db.execute(
                "INSERT OR IGNORE INTO sync_meta(key,value) VALUES('last_pull_id','0')"
            )
            db.execute("INSERT OR IGNORE INTO sync_meta(key,value) VALUES('last_sync_at','')")
            db.execute("INSERT OR IGNORE INTO sync_meta(key,value) VALUES('last_sync_status','never')")
            db.execute("INSERT OR IGNORE INTO sync_meta(key,value) VALUES('last_sync_error','')")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def enqueue(self, entity_type: str, entity_id: str, operation_type: str,
                base_version: int, payload: dict[str, Any], operation_id: str | None = None) -> str:
        if not entity_type or not entity_id:
            raise ValueError("entity_type et entity_id sont obligatoires")
        if operation_type not in {"create", "update", "delete", "transition"}:
            raise ValueError("Type d'opération offline invalide")
        if base_version < 0:
            raise ValueError("base_version invalide")
        operation_id = operation_id or str(uuid.uuid4())
        now = self._now()
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO sync_outbox
                (operation_id,school_id,device_id,entity_type,entity_id,operation_type,
                 base_version,payload_json,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (operation_id, self.school_id, self.device_id, entity_type, entity_id,
                 operation_type, base_version, json.dumps(payload, ensure_ascii=False),
                 "pending", now, now),
            )
        return operation_id

    def pending(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(int(limit), 1), 500)
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM sync_outbox WHERE status IN ('pending','retry') ORDER BY created_at LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._outbox_row(r) for r in rows]

    def mark_result(self, operation_id: str, status: str, server_version: int | None = None,
                    error: str | None = None):
        if status not in {"pending", "retry", "applied", "failed", "conflict"}:
            raise ValueError("Statut offline invalide")
        now = self._now()
        with self._lock, self._connect() as db:
            db.execute(
                """UPDATE sync_outbox SET status=?,server_version=?,error=?,updated_at=?
                   WHERE operation_id=?""",
                (status, server_version, error, now, operation_id),
            )
            if status == "conflict":
                row = db.execute("SELECT * FROM sync_outbox WHERE operation_id=?", (operation_id,)).fetchone()
                if row:
                    db.execute(
                        """INSERT OR REPLACE INTO sync_conflicts
                        (operation_id,entity_type,entity_id,base_version,server_version,payload_json,error)
                        VALUES(?,?,?,?,?,?,?)""",
                        (operation_id,row["entity_type"],row["entity_id"],row["base_version"],
                         server_version or 0,row["payload_json"],error),
                    )

    def conflicts(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM sync_conflicts WHERE resolution IS NULL ORDER BY operation_id").fetchall()
        return [dict(r) for r in rows]

    def resolve_conflict(self, operation_id: str, resolution: str):
        if resolution not in {"discard", "retry"}:
            raise ValueError("Résolution attendue: discard ou retry")
        now = self._now()
        with self._lock, self._connect() as db:
            conflict = db.execute("SELECT * FROM sync_conflicts WHERE operation_id=?", (operation_id,)).fetchone()
            if conflict is None:
                raise KeyError(operation_id)
            new_status = "pending" if resolution == "retry" else "failed"
            db.execute("UPDATE sync_conflicts SET resolution=?,resolved_at=? WHERE operation_id=?", (resolution, now, operation_id))
            db.execute("UPDATE sync_outbox SET status=?,error=?,updated_at=? WHERE operation_id=?", (new_status, None if resolution == "retry" else "Conflit abandonné localement", now, operation_id))

    def ingest_pull(self, items: list[dict[str, Any]], next_id: int | None = None) -> int:
        received = 0
        now = self._now()
        with self._lock, self._connect() as db:
            for item in items:
                payload = item.get("payload", {})
                cur = db.execute(
                    """INSERT OR IGNORE INTO sync_inbox
                    (operation_id,server_id,source_device_id,entity_type,entity_id,operation_type,
                     server_version,payload_json,status,received_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (item["operation_id"], item.get("id"), item.get("device_id"), item["entity_type"],
                     item["entity_id"], item["operation_type"], item.get("server_version"),
                     json.dumps(payload, ensure_ascii=False), "received", now),
                )
                received += int(cur.rowcount > 0)
            if next_id is not None:
                db.execute("UPDATE sync_meta SET value=? WHERE key='last_pull_id'", (str(next_id),))
        return received

    def inbox(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = min(max(int(limit), 1), 500)
        with self._connect() as db:
            rows = db.execute("SELECT * FROM sync_inbox WHERE status='received' ORDER BY server_id LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

    def mark_inbox_applied(self, operation_id: str):
        with self._lock, self._connect() as db:
            db.execute("UPDATE sync_inbox SET status='applied' WHERE operation_id=?", (operation_id,))

    def set_identity(self, entity_type: str, client_entity_id: str, server_entity_id: int):
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO sync_identity(entity_type,client_entity_id,server_entity_id) VALUES(?,?,?)",
                (entity_type, client_entity_id, server_entity_id),
            )

    def resolve_identity(self, entity_type: str, client_entity_id: str) -> int | None:
        with self._connect() as db:
            row = db.execute("SELECT server_entity_id FROM sync_identity WHERE entity_type=? AND client_entity_id=?", (entity_type, client_entity_id)).fetchone()
        return int(row[0]) if row else None


    def set_sync_state(self, status: str, error: str | None = None):
        now = self._now()
        with self._lock, self._connect() as db:
            db.execute("INSERT OR REPLACE INTO sync_meta(key,value) VALUES('last_sync_at',?)", (now,))
            db.execute("INSERT OR REPLACE INTO sync_meta(key,value) VALUES('last_sync_status',?)", (status,))
            db.execute("INSERT OR REPLACE INTO sync_meta(key,value) VALUES('last_sync_error',?)", (error or "",))

    def sync_state(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute("SELECT key,value FROM sync_meta WHERE key IN ('last_sync_at','last_sync_status','last_sync_error')").fetchall()
        data = {r[0]: r[1] for r in rows}
        return {
            "last_sync_at": data.get("last_sync_at") or None,
            "last_sync_status": data.get("last_sync_status") or "never",
            "last_sync_error": data.get("last_sync_error") or None,
        }

    def last_pull_id(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT value FROM sync_meta WHERE key='last_pull_id'").fetchone()[0])

    def summary(self) -> dict[str, int]:
        with self._connect() as db:
            out = db.execute("SELECT status,COUNT(*) n FROM sync_outbox GROUP BY status").fetchall()
            conflicts = db.execute("SELECT COUNT(*) FROM sync_conflicts WHERE resolution IS NULL").fetchone()[0]
            inbox = db.execute("SELECT COUNT(*) FROM sync_inbox WHERE status='received'").fetchone()[0]
        result = {"pending": 0, "retry": 0, "applied": 0, "failed": 0, "conflict": 0}
        result.update({r[0]: r[1] for r in out})
        result["unresolved_conflicts"] = int(conflicts)
        result["inbox_pending"] = int(inbox)
        return result

    @staticmethod
    def _outbox_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item
