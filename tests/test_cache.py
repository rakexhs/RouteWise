import numpy as np
import pytest

from app.cache import CacheManager
from app.cache.exact_cache import ExactCache
from app.cache.semantic_cache import SemanticCache
from app.cache.similarity import best_match, compute_similarity


def _embed(text: str) -> np.ndarray:
    mapping = {
        "what is python": np.array([1.0, 0.0, 0.0]),
        "explain python language": np.array([0.95, 0.05, 0.0]),
        "how to bake bread": np.array([0.0, 1.0, 0.0]),
    }
    key = text.lower().strip()
    for k, v in mapping.items():
        if k in key or key in k:
            return v
    return np.array([0.5, 0.5, 0.0])


def test_exact_cache_hit():
    cache = ExactCache(ttl_seconds=60)
    cache.set("key1", {"content": "answer"})
    val, meta = cache.get("key1")
    assert val["content"] == "answer"


def test_semantic_cache_above_threshold():
    semantic = SemanticCache(embed_fn=_embed, threshold=0.9, enabled=True)
    semantic.store("what is python", {"content": "Python is a language"})
    result = semantic.lookup("explain python language")
    assert result.hit is True
    assert result.confidence >= 0.9


def test_semantic_cache_below_threshold():
    semantic = SemanticCache(embed_fn=_embed, threshold=0.92, enabled=True)
    semantic.store("what is python", {"content": "Python is a language"})
    result = semantic.lookup("how to bake bread")
    assert result.hit is False


def test_semantic_cache_blocks_pii():
    semantic = SemanticCache(embed_fn=_embed, threshold=0.5, enabled=True)
    pii_prompt = "Contact me at user@example.com for details"
    semantic.store(pii_prompt, {"content": "no"})
    result = semantic.lookup(pii_prompt)
    assert result.hit is False


def test_cache_manager_exact_hit():
    manager = CacheManager(
        exact=ExactCache(ttl_seconds=60),
        semantic=SemanticCache(embed_fn=_embed, threshold=0.9, enabled=True),
    )
    manager.store("what is python", "hash1", {"content": "cached"})
    result = manager.lookup("what is python", "hash1")
    assert result.hit is True
    assert result.cache_status == "exact_hit"


def test_similarity_identical():
    a = np.array([1.0, 0.0])
    b = np.array([1.0, 0.0])
    assert compute_similarity(a, b) == pytest.approx(1.0, abs=0.01)
