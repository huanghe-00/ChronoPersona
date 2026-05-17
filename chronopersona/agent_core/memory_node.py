"""Memory retrieval node."""

from typing import Optional

from chronopersona.contracts.interfaces import AbstractMemoryStore
from chronopersona.contracts.schemas import RetrievedContext


class MemoryNode:
    """Retrieves context from L1/L2 memory layers."""

    def __init__(self, memory_store: AbstractMemoryStore) -> None:
        self._memory_store = memory_store

    def retrieve(self, query: str, branch_id: str, intent: Optional[str] = None) -> RetrievedContext:
        """Retrieve relevant memories for the given query."""
        return self._memory_store.retrieve(query, branch_id, intent=intent or "retrieve")
