import json
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    value: dict[str, Any]
    expires_at: float
    metadata: dict[str, Any]


class ExactCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._redis = None
        self._use_redis = False
        self._init_redis()

    def _init_redis(self) -> None:
        from app.config import get_settings

        settings = get_settings()
        if not settings.redis_url:
            return
        try:
            import redis

            client = redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            self._use_redis = True
        except Exception:
            self._redis = None
            self._use_redis = False

    def get(self, key: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if self._use_redis and self._redis:
            raw = self._redis.get(f"exact:{key}")
            if raw:
                data = json.loads(raw)
                return data["value"], data.get("metadata")
            return None, None

        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None, None
            if time.time() > entry.expires_at:
                del self._store[key]
                return None, None
            return entry.value, entry.metadata

    def set(self, key: str, value: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        metadata = metadata or {}
        if self._use_redis and self._redis:
            payload = json.dumps({"value": value, "metadata": metadata})
            self._redis.setex(f"exact:{key}", self.ttl_seconds, payload)
            return

        with self._lock:
            self._store[key] = CacheEntry(
                value=value,
                expires_at=time.time() + self.ttl_seconds,
                metadata=metadata,
            )

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
