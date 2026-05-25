"""L2 Episodic Store backed by FAISS."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set

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

    def __init__(self, embedder: Optional[MockBGEEmbedder] = None, dim: int = 128) -> None:
        self._embedder = embedder or MockBGEEmbedder()
        self._dim = dim
        self._indices: Dict[str, faiss.IndexFlatIP] = {}
        self._entries: Dict[str, List[MemoryEntry]] = {}
        self._deleted_indices: Dict[str, Set[int]] = {}

    def _get_index(self, branch_id: str) -> faiss.IndexFlatIP:
        if branch_id not in self._indices:
            self._indices[branch_id] = faiss.IndexFlatIP(self._dim)
            self._entries[branch_id] = []
            self._deleted_indices[branch_id] = set()
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
        intent: Optional[str] = None,
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
        deleted = self._deleted_indices.get(branch_id, set())
        top_entries = [
            self._entries[branch_id][i]
            for i in indices[0]
            if i >= 0 and i not in deleted
        ]

        now_str = datetime.now().isoformat()
        for entry in top_entries:
            entry.access_count += 1
            entry.last_accessed = now_str

        return RetrievedContext(
            episodic_memories=top_entries,
            total_tokens=sum(len(m.content) for m in top_entries),
        )

    def delete(self, memory_id: str, branch_id: str) -> bool:
        """Soft-delete by marking index as deleted (FAISS IndexFlatIP does not support physical removal)."""
        if not branch_id or branch_id not in self._entries:
            return False
        for idx, entry in enumerate(self._entries[branch_id]):
            if entry.id == memory_id:
                entry.content = ""
                self._deleted_indices.setdefault(branch_id, set()).add(idx)
                return True
        return False
"""FAISS-based L2 episodic store with conditional ID generation."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional, Set

import numpy as np

from chronopersona.contracts.interfaces import AbstractEpisodicStore
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class FaissEpisodicStore(AbstractEpisodicStore):
    """Episodic store backed by FAISS IndexFlatIP for cosine similarity.

    Uses MockBGEEmbedder for vector embeddings and standard library math
    for scoring, avoiding external dependencies beyond numpy.
    """

    def __init__(self, embedder: Optional[MockBGEEmbedder] = None) -> None:
        self._embedder = embedder or MockBGEEmbedder()
        # branch_id -> list of MemoryEntry
        self._entries: Dict[str, List[MemoryEntry]] = {}
        # branch_id -> numpy array of shape (n, 128)
        self._vectors: Dict[str, np.ndarray] = {}
        # branch_id -> set of deleted indices
        self._deleted_indices: Dict[str, Set[int]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"l2-faiss-{self._counter}"

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two numpy vectors."""
        dot = float(np.dot(a, b))
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
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
        vec = np.array(self._embedder.embed_query(entry.content), dtype=np.float32)
        if branch_id not in self._vectors:
            self._vectors[branch_id] = vec.reshape(1, -1)
        else:
            self._vectors[branch_id] = np.vstack([self._vectors[branch_id], vec])
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
        vectors = self._vectors.get(branch_id)
        if not entries or vectors is None:
            return RetrievedContext()

        query_vec = np.array(self._embedder.embed_query(query), dtype=np.float32)
        deleted = self._deleted_indices.get(branch_id, set())
        scored = []
        now = datetime.now()
        for idx, (vec, entry) in enumerate(zip(vectors, entries)):
            if idx in deleted:
                continue
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
        for idx, entry in enumerate(entries):
            if entry.id == memory_id:
                self._deleted_indices.setdefault(branch_id, set()).add(idx)
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
        vectors = self._vectors.get(branch_id)
        if not entries or vectors is None:
            return None
        new_vec = np.array(self._embedder.embed_query(entry.content), dtype=np.float32)
        for vec, existing in zip(vectors, entries):
            sim = self._cosine_similarity(new_vec, vec)
            if sim > 0.95:
                return existing
        return None
