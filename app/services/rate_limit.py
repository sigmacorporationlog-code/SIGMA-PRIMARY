"""Débit adaptatif: Redis partagé en multi-instance, mémoire sinon."""
from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from app.core.config import settings

logger = logging.getLogger("sigma.rate_limit")


class RateLimitExceeded(Exception):
    """La limite de débit configurée a été atteinte."""


class InMemoryRateLimiter:
    def __init__(self, max_keys: int = 50_000) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._last_seen: dict[str, float] = {}
        self._max_keys = max(1_000, int(max_keys))
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                self._last_seen[key] = now
                raise RateLimitExceeded()
            bucket.append(now)
            self._last_seen[key] = now
            if len(self._events) > self._max_keys:
                stale = sorted(self._last_seen.items(), key=lambda item: item[1])[: max(1, len(self._events) - self._max_keys)]
                for stale_key, _ in stale:
                    self._events.pop(stale_key, None)
                    self._last_seen.pop(stale_key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._last_seen.clear()


class RedisRateLimiter:
    _SCRIPT = """
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
local window_ms = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local cutoff = now_ms - window_ms
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, cutoff)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  return 0
end
redis.call('ZADD', KEYS[1], now_ms, ARGV[3])
redis.call('EXPIRE', KEYS[1], math.max(1, math.ceil(window_ms / 1000) + 1))
return 1
"""

    def __init__(self, url: str, prefix: str) -> None:
        from redis import Redis
        self.client = Redis.from_url(url, decode_responses=True, socket_timeout=1.0, socket_connect_timeout=1.0)
        self.prefix = prefix
        self.script = self.client.register_script(self._SCRIPT)

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        redis_key = f"{self.prefix}{key}"
        allowed = self.script(keys=[redis_key], args=[int(window_seconds * 1000), int(limit), uuid.uuid4().hex])
        if int(allowed or 0) != 1:
            raise RateLimitExceeded()


_LOCAL = InMemoryRateLimiter()
_REMOTE = None
_REMOTE_FAILED_LOGGED = False


def _backend():
    global _REMOTE, _REMOTE_FAILED_LOGGED
    if not settings.RATE_LIMIT_REDIS_URL:
        return _LOCAL
    if _REMOTE is not None:
        return _REMOTE
    try:
        _REMOTE = RedisRateLimiter(settings.RATE_LIMIT_REDIS_URL, settings.RATE_LIMIT_REDIS_PREFIX)
        _REMOTE.client.ping()
        return _REMOTE
    except Exception as exc:
        if not _REMOTE_FAILED_LOGGED:
            logger.warning("Rate limiter Redis indisponible: %s", exc)
            _REMOTE_FAILED_LOGGED = True
        _REMOTE = None
        if getattr(settings, "RATE_LIMIT_FAIL_CLOSED", False):
            raise RuntimeError("Rate limiter distribué indisponible") from exc
        return _LOCAL


class AdaptiveRateLimiter:
    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        _backend().check(key, limit=limit, window_seconds=window_seconds)

    def clear_local(self) -> None:
        _LOCAL.clear()


limiter = AdaptiveRateLimiter()
