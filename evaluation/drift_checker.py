"""Persona drift detection using embedding similarity baseline."""

import math
from typing import List

from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class PersonaDriftChecker:
    """MVA-level drift detector using MockBGEEmbedder embeddings.

    W8+: Replace with sentence-transformers for production-grade semantic similarity.
    """

    def __init__(self, style_examples: List[str]) -> None:
        self._embedder = MockBGEEmbedder()
        self._baseline = self._compute_baseline(style_examples)

    def _compute_baseline(self, examples: List[str]) -> List[float]:
        if not examples:
            return []
        vectors = [self._embedder.embed_query(ex) for ex in examples]
        dim = len(vectors[0])
        return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]

    def check(self, reply: str) -> float:
        """Return cosine similarity between reply and style baseline."""
        if not self._baseline:
            return 0.0
        vec = self._embedder.embed_query(reply)
        return self._cosine_similarity(vec, self._baseline)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
