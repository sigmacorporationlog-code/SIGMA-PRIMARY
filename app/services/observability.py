"""Lightweight in-process performance and observability metrics for SIGMA.

The collector is intentionally dependency-free and safe for the Windows build.
It provides rolling request metrics without storing request bodies, tokens, or PII.
"""
from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic
from typing import Any
from contextvars import ContextVar
import logging
import re

from app.core.config import settings

_MAX_SAMPLES = max(100, settings.OBSERVABILITY_SAMPLE_LIMIT)
_lock = Lock()
_started = monotonic()
_total_requests = 0
_total_errors = 0
_samples: deque[dict[str, Any]] = deque(maxlen=_MAX_SAMPLES)
_request_id_ctx: ContextVar[str] = ContextVar("sigma_request_id", default="-")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def normalize_request_id(candidate: str | None) -> str:
    value = (candidate or "").strip()
    return value if _REQUEST_ID_RE.fullmatch(value) else __import__("uuid").uuid4().hex


def set_request_id(value: str):
    return _request_id_ctx.set(normalize_request_id(value))


def reset_request_id(token) -> None:
    _request_id_ctx.reset(token)


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def install_logging_context() -> None:
    root = logging.getLogger()
    filt = RequestIdFilter()
    root.addFilter(filt)
    for handler in root.handlers:
        handler.addFilter(filt)


def record_request(method: str, path: str, status_code: int, duration_ms: float, request_id: str | None = None) -> None:
    global _total_requests, _total_errors
    # Normalize dynamic paths so metrics don't explode in cardinality.
    normalized = path.split("?")[0]
    with _lock:
        _total_requests += 1
        if status_code >= 500:
            _total_errors += 1
        _samples.append({
            "method": method.upper(),
            "path": normalized[:240],
            "status_code": int(status_code),
            "duration_ms": round(float(duration_ms), 2),
        })


def snapshot() -> dict[str, Any]:
    with _lock:
        samples = list(_samples)
        total = _total_requests
        errors = _total_errors
    durations = sorted(x["duration_ms"] for x in samples)
    by_status: dict[str, int] = {}
    by_path: dict[str, dict[str, Any]] = {}
    for item in samples:
        code = str(item["status_code"])
        by_status[code] = by_status.get(code, 0) + 1
        key = f'{item["method"]} {item["path"]}'
        row = by_path.setdefault(key, {"requests": 0, "errors": 0, "avg_ms": 0.0, "max_ms": 0.0})
        row["requests"] += 1
        row["errors"] += int(item["status_code"] >= 500)
        row["avg_ms"] += item["duration_ms"]
        row["max_ms"] = max(row["max_ms"], item["duration_ms"])
    for row in by_path.values():
        row["avg_ms"] = round(row["avg_ms"] / row["requests"], 2)
    def percentile(p: float) -> float:
        if not durations:
            return 0.0
        idx = min(len(durations) - 1, max(0, int(round((len(durations) - 1) * p))))
        return round(durations[idx], 2)
    return {
        "uptime_seconds": round(monotonic() - _started, 2),
        "total_requests": total,
        "total_5xx": errors,
        "rolling_samples": len(samples),
        "error_rate_5xx_percent": round((errors / total) * 100, 3) if total else 0.0,
        "latency_ms": {"p50": percentile(.50), "p95": percentile(.95), "p99": percentile(.99), "max": round(max(durations), 2) if durations else 0.0},
        "status_counts": by_status,
        "slowest_routes": sorted(
            ({"route": k, **v} for k, v in by_path.items()),
            key=lambda x: (x["max_ms"], x["avg_ms"]), reverse=True,
        )[:10],
    }
