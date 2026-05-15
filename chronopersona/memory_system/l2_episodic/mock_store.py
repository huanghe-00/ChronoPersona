"""Mock episodic memory store for L2."""

from typing import Dict, List, Optional

from chronopersona.contracts.interfaces.abstract_episodic_store import AbstractEpisodicStore
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class MockEpisodicStore(AbstractEpisodicStore):
    """In-memory mock implementation of L2 episodic store."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, MemoryEntry]] = {}  # branch_id -> {memory_id: entry}
        self._embedder = MockBGEEmbedder()
        self._counter = 0

    def add(self, entry: MemoryEntry, branch_id: str) -> str:
        """Add a memory entry and return its ID."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._counter += 1
        memory_id = f"l2-mem-{self._counter}"
        if branch_id not in self._store:
            self._store[branch_id] = {}
        self._store[branch_id][memory_id] = entry
        return memory_id

    def retrieve(
        self,
        query: str,
        branch_id: str,
        top_k: int = 5,
        intent: Optional[str] = None,
    ) -> RetrievedContext:
        """Retrieve relevant memories using mock similarity."""
        if branch_id not in self._store:
            return RetrievedContext(
                episodic_memories=[],
                working_memories=[],
                semantic_facts=[],
                insights=[],
                navigation_path=[],
                total_tokens=0,
            )

        query_vec = self._embedder.embed_query(query)
        entries = list(self._store[branch_id].values())

        # Simple mock similarity based on content overlap
        scored = []
        for entry in entries:
            overlap = len(set(query) & set(entry.content))
            scored.append((overlap, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_entries = [entry for _, entry in scored[:top_k]]

        return RetrievedContext(
            episodic_memories=top_entries,
            working_memories=[],
            semantic_facts=[],
            insights=[],
            navigation_path=[],
            total_tokens=sum(len(e.content) for e in top_entries),
        )

    def delete(self, memory_id: str, branch_id: str) -> bool:
        """Delete a memory entry."""
        if branch_id in self._store and memory_id in self._store[branch_id]:
            del self._store[branch_id][memory_id]
            return True
        return False
