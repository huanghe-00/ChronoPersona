"""Simple in-memory L2 episodic store using MockBGEEmbedder and cosine similarity."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractEpisodicStore
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class SimpleEpisodicStore(AbstractEpisodicStore):
    """In-memory episodic store with cosine similarity retrieval.

    Uses MockBGEEmbedder for vector embeddings and standard library math
    for cosine similarity, avoiding external dependencies.
    """

    def __init__(self, embedder: Optional[MockBGEEmbedder] = None) -> None:
        self._embedder = embedder or MockBGEEmbedder()
        # branch_id -> list of MemoryEntry
        self._entries: Dict[str, List[MemoryEntry]] = {}
        # branch_id -> list of embedding vectors (list[float])
        self._vectors: Dict[str, List[List[float]]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"l2-simple-{self._counter}"

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors using math."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add(self, entry: MemoryEntry, branch_id: str) -> str:
        """Add a memory entry and its embedding to the store.

        Returns:
            The assigned memory id.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        # Near-duplicate detection
        existing = self._find_near_duplicate(entry, branch_id)
        if existing is not None:
            existing.access_count += 1
            existing.last_accessed = datetime.now().isoformat()
            if len(entry.content) > len(existing.content):
                existing.content = entry.content
            return existing.id
        mid = self._next_id()
        entry.id = mid
        self._entries.setdefault(branch_id, []).append(entry)
        vec = self._embedder.embed_query(entry.content)
        self._vectors.setdefault(branch_id, []).append(vec)
        return mid

    def retrieve(
        self,
        query: str,
        branch_id: str,
        top_k: int = 5,
        intent: Optional[str] = None,
    ) -> RetrievedContext:
        """Retrieve top-k most similar memories for the given query.

        Returns:
            RetrievedContext with episodic_memories populated.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        entries = self._entries.get(branch_id, [])
        vectors = self._vectors.get(branch_id, [])
        if not entries:
            return RetrievedContext()

        query_vec = self._embedder.embed_query(query)
        scored = []
        now = datetime.now()
        for vec, entry in zip(vectors, entries):
            sim = self._cosine_similarity(query_vec, vec)
            importance = max(entry.importance, 0.01)
            
            # 30-day half-life decay for access_count
            try:
                last_access = datetime.fromisoformat(entry.last_accessed or "")
                days_elapsed = max((now - last_access).days, 0)
            except (ValueError, TypeError):
                days_elapsed = 0
            effective_access = entry.access_count * math.exp(-days_elapsed / 30.0)
            freq_boost = 1.0 + math.log1p(effective_access)
            
            score = sim * importance * freq_boost
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        now_str = datetime.now().isoformat()
        top = []
        for _, entry in scored[:top_k]:
            entry.access_count += 1
            entry.last_accessed = now_str
            top.append(entry)
        return RetrievedContext(
            episodic_memories=top,
            total_tokens=sum(len(m.content) for m in top),
        )

    def delete(self, memory_id: str, branch_id: str) -> bool:
        """Delete a memory entry by id.

        Returns:
            True if the entry was found and removed, False otherwise.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        entries = self._entries.get(branch_id, [])
        vectors = self._vectors.get(branch_id, [])
        for idx, entry in enumerate(entries):
            if entry.id == memory_id:
                del entries[idx]
                del vectors[idx]
                return True
        return False

    def _find_near_duplicate(self, entry: MemoryEntry, branch_id: str) -> Optional[MemoryEntry]:
        """Return existing entry if similarity > 0.95, else None.

        NOTE: MockBGEEmbedder generates vectors based on text length only.
        Identical lengths yield similarity 1.0; different lengths yield ~0.0.
        Production embedders (sentence-transformers) will correctly detect
        semantic near-duplicates regardless of length differences.
        """
        entries = self._entries.get(branch_id, [])
        vectors = self._vectors.get(branch_id, [])
        if not entries:
            return None
        new_vec = self._embedder.embed_query(entry.content)
        for vec, existing in zip(vectors, entries):
            sim = self._cosine_similarity(new_vec, vec)
            if sim > 0.95:
                return existing
        return None
