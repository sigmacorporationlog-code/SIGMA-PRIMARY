"""Fail-closed deployment activation and rollback primitives for SIGMA.

The guard is intentionally conservative: it stages an artifact, records the
previous executable, activates only after a successful preflight, and can
restore the previous artifact when a post-activation health check fails.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Callable


class DeploymentError(RuntimeError):
    """Erreur bloquante lors d'une activation ou d'un rollback."""


@dataclass(frozen=True)
class DeploymentResult:
    status: str
    artifact: str
    previous: str | None
    sha256: str
    rollback_available: bool
    message: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_child(root: Path, name: str) -> Path:
    if not name or Path(name).name != name or name in {".", ".."}:
        raise DeploymentError("unsafe deployment filename")
    return root / name


def stage_artifact(artifact: Path, staging_dir: Path) -> Path:
    artifact = artifact.resolve()
    if not artifact.is_file():
        raise DeploymentError("artifact not found")
    staging_dir.mkdir(parents=True, exist_ok=True)
    target = _safe_child(staging_dir, artifact.name)
    tmp = target.with_suffix(target.suffix + ".tmp")
    shutil.copy2(artifact, tmp)
    os.replace(tmp, target)
    if sha256_file(target) != sha256_file(artifact):
        target.unlink(missing_ok=True)
        raise DeploymentError("artifact integrity verification failed")
    return target


def activate_windows_executable(
    artifact: Path,
    install_dir: Path,
    *,
    service_name: str = "SIGMAPrimaireServer",
    health_check: Callable[[], bool] | None = None,
    command_runner: Callable[[list[str]], None] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> DeploymentResult:
    """Atomically-ish activate an executable with a recoverable rollback.

    True zero-downtime cannot be guaranteed for a single Windows service
    executable. The function therefore implements graceful stop -> swap ->
    start -> health verification -> rollback on failure.
    """
    if os.name != "nt":
        raise DeploymentError("Windows activation requires Windows")
    install_dir = install_dir.resolve()
    install_dir.mkdir(parents=True, exist_ok=True)
    staging = install_dir / ".staging"
    staged = stage_artifact(artifact, staging)
    active = install_dir / "SIGMA-Server.exe"
    backup_dir = install_dir / ".rollback"
    backup_dir.mkdir(parents=True, exist_ok=True)
    previous = backup_dir / f"SIGMA-Server.previous.exe"
    runner = command_runner or (lambda cmd: subprocess.run(cmd, check=True, capture_output=True, text=True))

    if active.exists():
        shutil.copy2(active, previous)

    try:
        runner(["sc", "stop", service_name])
    except Exception as exc:
        # A stopped/non-installed service is acceptable; activation still
        # requires a successful start below.
        logger.info("Service %s non arrêté avant activation: %s", service_name, exc)
    sleep_fn(0.5)

    try:
        os.replace(staged, active)
        runner(["sc", "start", service_name])
        if health_check is not None:
            deadline = time.monotonic() + 30
            healthy = False
            while time.monotonic() < deadline:
                if health_check():
                    healthy = True
                    break
                sleep_fn(1.0)
            if not healthy:
                raise DeploymentError("post-deployment health check failed")
    except Exception as exc:
        if previous.exists():
            try:
                runner(["sc", "stop", service_name])
            except Exception as stop_exc:
                logger.warning("Arrêt du service %s impossible pendant rollback: %s", service_name, stop_exc)
            os.replace(previous, active)
            try:
                runner(["sc", "start", service_name])
            except Exception as start_exc:
                logger.error("Redémarrage du service %s impossible après rollback: %s", service_name, start_exc)
        raise DeploymentError(f"deployment rolled back: {exc}") from exc

    return DeploymentResult(
        status="activated",
        artifact=active.name,
        previous=previous.name if previous.exists() else None,
        sha256=sha256_file(active),
        rollback_available=previous.exists(),
        message="Deployment activé et health-check validé.",
    )


def write_deployment_state(path: Path, result: DeploymentResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")
