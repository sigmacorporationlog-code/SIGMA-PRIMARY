"""Capacity and performance diagnostics for SIGMA.

The module is intentionally dependency-light. It exposes deterministic,
read-only diagnostics that can be used by the control center and deployment
checks without requiring a monitoring stack.
"""
from __future__ import annotations

import os
import platform
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import engine, is_sqlite
from app.services.observability import snapshot


def _pool_status() -> dict:
    pool = getattr(engine, "pool", None)
    if pool is None or is_sqlite:
        return {"type": "sqlite", "checked_out": None, "size": None, "overflow": None}
    try:
        return {
            "type": type(pool).__name__,
            "checked_out": pool.checkedout(),
            "size": pool.size(),
            "overflow": pool.overflow(),
            "timeout_seconds": settings.DB_POOL_TIMEOUT_SECONDS,
        }
    except Exception as exc:
        return {"type": type(pool).__name__, "error": str(exc)[:200]}


def capacity_snapshot() -> dict:
    metrics = snapshot()
    pool = _pool_status()
    cpu = os.cpu_count() or 1
    p95 = metrics["latency_ms"]["p95"]
    error_rate = metrics["error_rate_5xx_percent"]
    warnings: list[str] = []
    if p95 >= settings.SLOW_REQUEST_THRESHOLD_MS:
        warnings.append("latence p95 au-dessus du seuil configuré")
    if error_rate >= 1.0:
        warnings.append("taux HTTP 5xx supérieur ou égal à 1%")
    if pool.get("checked_out") is not None and pool.get("size"):
        ratio = pool["checked_out"] / max(1, pool["size"])
        if ratio >= 0.9:
            warnings.append("pool SQL proche de la saturation")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "cpu_count": cpu,
        "database": {"engine": "sqlite" if is_sqlite else "external", "pool": pool},
        "limits": {
            "db_pool_size": settings.DB_POOL_SIZE,
            "db_max_overflow": settings.DB_MAX_OVERFLOW,
            "gzip_enabled": settings.GZIP_ENABLED,
            "slow_request_threshold_ms": settings.SLOW_REQUEST_THRESHOLD_MS,
            "observability_sample_limit": settings.OBSERVABILITY_SAMPLE_LIMIT,
        },
        "observability": metrics,
        "warnings": warnings,
        "status": "warning" if warnings else "ok",
    }
