import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    a = vec_a.reshape(1, -1)
    b = vec_b.reshape(1, -1)
    return float(cosine_similarity(a, b)[0][0])


def best_match(
    query: np.ndarray, candidates: list[np.ndarray], threshold: float
) -> tuple[int | None, float]:
    if not candidates:
        return None, 0.0
    best_idx = None
    best_score = -1.0
    for i, candidate in enumerate(candidates):
        score = compute_similarity(query, candidate)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_idx is not None and best_score >= threshold:
        return best_idx, best_score
    return None, best_score
