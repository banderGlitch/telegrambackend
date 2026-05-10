"""Optional Redis connection for caching and shared state across replicas.

If ``REDIS_URL`` is empty or Redis is unreachable at first use, all helpers
return ``None`` / no-op and the API keeps working without cache.
"""

from __future__ import annotations

import logging
import threading

import redis

from .config import get_settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_pool: redis.ConnectionPool | None = None
_client: redis.Redis | None = None
_redis_failed: bool = False


def get_redis() -> redis.Redis | None:
    """Return a shared client, or ``None`` if Redis is disabled or unavailable."""
    global _pool, _client, _redis_failed

    if _redis_failed:
        return None
    url = get_settings().redis_url.strip()
    if not url:
        return None
    if _client is not None:
        return _client

    with _lock:
        if _redis_failed:
            return None
        if _client is not None:
            return _client
        try:
            _pool = redis.ConnectionPool.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
                health_check_interval=30,
            )
            _client = redis.Redis(connection_pool=_pool)
            _client.ping()
            log.info("Redis connected for optional cache")
            return _client
        except Exception as exc:
            _redis_failed = True
            _client = None
            if _pool is not None:
                try:
                    _pool.disconnect()
                except Exception:
                    pass
                _pool = None
            log.warning("Redis disabled: %s", exc)
            return None


def close_redis() -> None:
    """Release the connection pool (called from app shutdown)."""
    global _pool, _client, _redis_failed
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        if _pool is not None:
            try:
                _pool.disconnect()
            except Exception:
                pass
        _client = None
        _pool = None
        _redis_failed = False
