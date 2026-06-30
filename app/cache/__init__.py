from dataclasses import dataclass
from typing import Any

from app.cache.exact_cache import ExactCache
from app.cache.semantic_cache import SemanticCache, SemanticCacheResult
from app.config import get_settings
from app.gateway.router import normalize_prompt


@dataclass
class CacheLookupResult:
    hit: bool
    cache_status: str
    value: dict[str, Any] | None
    confidence: float | None
    metadata: dict[str, Any] | None


class CacheManager:
    def __init__(
        self,
        exact: ExactCache | None = None,
        semantic: SemanticCache | None = None,
    ) -> None:
        settings = get_settings()
        self.exact = exact or ExactCache(ttl_seconds=settings.exact_cache_ttl_seconds)
        self.semantic = semantic or SemanticCache()

    def lookup(self, prompt: str, cache_key: str) -> CacheLookupResult:
        exact_val, exact_meta = self.exact.get(cache_key)
        if exact_val:
            return CacheLookupResult(
                hit=True,
                cache_status="exact_hit",
                value=exact_val,
                confidence=1.0,
                metadata=exact_meta,
            )

        semantic_result: SemanticCacheResult = self.semantic.lookup(prompt)
        if semantic_result.hit:
            return CacheLookupResult(
                hit=True,
                cache_status="semantic_hit",
                value=semantic_result.value,
                confidence=semantic_result.confidence,
                metadata=semantic_result.metadata,
            )

        return CacheLookupResult(
            hit=False,
            cache_status="miss",
            value=None,
            confidence=semantic_result.confidence if semantic_result.confidence > 0 else None,
            metadata=None,
        )

    def store(
        self,
        prompt: str,
        cache_key: str,
        value: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.exact.set(cache_key, value, metadata)
        self.semantic.store(prompt, value, metadata)

    def clear(self) -> None:
        self.exact.clear()
        self.semantic.clear()


def combined_prompt_text(messages: list[dict[str, str]]) -> str:
    return normalize_prompt(" ".join(m["content"] for m in messages))
