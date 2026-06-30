import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException

from app.config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._redis = None
        self._use_redis = False
        self._init_redis()

    def _init_redis(self) -> None:
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

    def check(self, api_key: str) -> None:
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        now = time.time()
        window_start = now - 60

        if self._use_redis and self._redis:
            key = f"ratelimit:{api_key}"
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, 60)
            _, _, count, _ = pipe.execute()
            if int(count) > limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            return

        with self._lock:
            bucket = self._buckets[api_key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            bucket.append(now)


rate_limiter = RateLimiter()
