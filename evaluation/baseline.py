"""Pure vector RAG baseline for comparison.

Uses SimpleEpisodicStore (cosine similarity) as the default backend
to provide a realistic baseline for evaluation scenarios.
"""

from __future__ import annotations

from typing import Dict, List

from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.memory_system.l2_episodic import SimpleEpisodicStore


class VectorRAGBaseline:
    """Baseline using only vector similarity (no intent graph)."""

    def __init__(self) -> None:
        self._store = SimpleEpisodicStore()
        self._id_map: Dict[str, str] = {}

    def index(self, memories: List[MemoryEntry], branch_id: str) -> None:
        """Index memories for retrieval."""
        for mem in memories:
            original_id = mem.id or "unknown"
            store_id = self._store.add(mem, branch_id=branch_id)
            self._id_map[store_id] = original_id

    def retrieve(self, query: str, branch_id: str, top_k: int = 5) -> List[str]:
        """Retrieve top-k memory IDs using vector similarity only."""
        ctx = self._store.retrieve(query, branch_id=branch_id, top_k=top_k)
        return [self._id_map.get(m.id, m.id) for m in ctx.episodic_memories]
