"""L2 Episodic Store backed by FAISS."""

from __future__ import annotations

from typing import Dict, List

import faiss
import numpy as np

from chronopersona.contracts.interfaces import AbstractEpisodicStore
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class FaissEpisodicStore(AbstractEpisodicStore):
    """Production-grade episodic store using FAISS ANN index per branch.

    Uses IndexFlatIP (exact inner product) with L2 normalization to
    achieve cosine similarity. Each branch maintains an independent
    FAISS index for strict isolation.
    """

    def __init__(self, embedder: MockBGEEmbedder | None = None, dim: int = 128) -> None:
        self._embedder = embedder or MockBGEEmbedder()
        self._dim = dim
        self._indices: Dict[str, faiss.IndexFlatIP] = {}
        self._entries: Dict[str, List[MemoryEntry]] = {}

    def _get_index(self, branch_id: str) -> faiss.IndexFlatIP:
        if branch_id not in self._indices:
            self._indices[branch_id] = faiss.IndexFlatIP(self._dim)
            self._entries[branch_id] = []
        return self._indices[branch_id]

    def add(self, entry: MemoryEntry, branch_id: str) -> str:
        """Add a memory entry to the branch-specific FAISS index."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        vec = np.array([self._embedder.embed_query(entry.content)], dtype=np.float32)
        faiss.normalize_L2(vec)

        index = self._get_index(branch_id)
        index.add(vec)

        idx = len(self._entries[branch_id])
        entry.id = entry.id or f"faiss-{branch_id}-{idx}"
        self._entries[branch_id].append(entry)
        return entry.id

    def retrieve(
        self,
        query: str,
        branch_id: str,
        top_k: int = 5,
        intent: str | None = None,
    ) -> RetrievedContext:
        """Retrieve top-k memories using FAISS cosine similarity."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if branch_id not in self._indices:
            return RetrievedContext(episodic_memories=[], total_tokens=0)

        vec = np.array([self._embedder.embed_query(query)], dtype=np.float32)
        faiss.normalize_L2(vec)

        index = self._indices[branch_id]
        actual_k = min(top_k, len(self._entries[branch_id]))
        if actual_k == 0:
            return RetrievedContext(episodic_memories=[], total_tokens=0)

        scores, indices = index.search(vec, actual_k)
        top_entries = [self._entries[branch_id][i] for i in indices[0] if i >= 0]

        return RetrievedContext(
            episodic_memories=top_entries,
            total_tokens=sum(len(m.content) for m in top_entries),
        )

    def delete(self, memory_id: str, branch_id: str) -> bool:
        """Soft-delete by clearing content (FAISS IndexFlatIP does not support efficient deletion)."""
        if not branch_id or branch_id not in self._entries:
            return False
        for entry in self._entries[branch_id]:
            if entry.id == memory_id:
                entry.content = ""
                return True
        return False
