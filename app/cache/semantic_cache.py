from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from app.cache.similarity import best_match
from app.config import get_settings
from app.gateway.pii_redactor import detect_pii


@dataclass
class SemanticCacheEntry:
    embedding: np.ndarray
    value: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class SemanticCacheResult:
    hit: bool
    value: dict[str, Any] | None
    confidence: float
    metadata: dict[str, Any] | None


class SemanticCache:
    def __init__(
        self,
        embed_fn: Callable[[str], np.ndarray] | None = None,
        threshold: float | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.threshold = threshold if threshold is not None else settings.semantic_similarity_threshold
        self.enabled = settings.semantic_cache_enabled if enabled is None else enabled
        self._entries: list[SemanticCacheEntry] = []
        self._embed_fn = embed_fn or self._default_embed_fn
        self._model = None

    def _default_embed_fn(self, text: str) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        vec = self._model.encode(text, normalize_embeddings=True)
        return np.array(vec, dtype=np.float32)

    def lookup(self, prompt: str) -> SemanticCacheResult:
        if not self.enabled:
            return SemanticCacheResult(hit=False, value=None, confidence=0.0, metadata=None)
        if detect_pii(prompt).has_pii:
            return SemanticCacheResult(hit=False, value=None, confidence=0.0, metadata=None)

        query = self._embed_fn(prompt)
        idx, score = best_match(query, [e.embedding for e in self._entries], self.threshold)
        if idx is None:
            return SemanticCacheResult(hit=False, value=None, confidence=score, metadata=None)
        entry = self._entries[idx]
        return SemanticCacheResult(
            hit=True,
            value=entry.value,
            confidence=score,
            metadata=entry.metadata,
        )

    def store(self, prompt: str, value: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        if detect_pii(prompt).has_pii:
            return
        embedding = self._embed_fn(prompt)
        self._entries.append(
            SemanticCacheEntry(
                embedding=embedding,
                value=value,
                metadata=metadata or {},
            )
        )

    def clear(self) -> None:
        self._entries.clear()
