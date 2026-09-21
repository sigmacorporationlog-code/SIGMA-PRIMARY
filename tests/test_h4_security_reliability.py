from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from app.services.client_updater import UpdateError, update_client
from app.services.rate_limit import InMemoryRateLimiter, RateLimitExceeded
from app.services.update_agent import UpdateAgentError, UpdateManifest, acquire_lock, release_lock


def make_zip(path: Path, member_name: str, payload: bytes = b"ok") -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, payload)


def test_client_updater_rejects_zip_traversal(tmp_path: Path):
    package = tmp_path / "malicious.zip"
    make_zip(package, "SIGMA/../../escape.txt")
    manifest = {
        "version": "4.46.1",
        "package_sha256": __import__("hashlib").sha256(package.read_bytes()).hexdigest(),
        "package_size": package.stat().st_size,
        "package_url": package.as_uri(),
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(UpdateError, match="ZIP dangereux"):
        update_client(
            current_version="4.46.0",
            manifest_path=manifest_path,
            install_dir=tmp_path / "install",
            backup_root=tmp_path / "backup",
        )


def test_update_agent_rejects_plain_http():
    with pytest.raises(UpdateAgentError, match="HTTPS ou file"):
        UpdateManifest.from_dict({
            "version": "4.46.1",
            "url": "http://example.invalid/update.zip",
            "sha256": "a" * 64,
            "size_bytes": 10,
        })


def test_rate_limiter_bounds_keys_and_enforces_limit():
    limiter = InMemoryRateLimiter(max_keys=1000)
    for idx in range(1100):
        limiter.check(f"key-{idx}", limit=1, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        limiter.check("hot", limit=1, window_seconds=60)
        limiter.check("hot", limit=1, window_seconds=60)
    assert len(limiter._events) <= 1000


def test_update_lock_recovers_dead_process_lock(tmp_path: Path):
    lock = tmp_path / "update.lock"
    lock.write_text("999999999", encoding="ascii")
    acquire_lock(lock)
    try:
        assert lock.read_text(encoding="ascii") == str(os.getpid())
    finally:
        release_lock(lock)
    assert not lock.exists()
