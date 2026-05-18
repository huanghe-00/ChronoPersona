"""Memory retrieval node."""

from typing import Optional

from chronopersona.contracts.interfaces import AbstractMemoryStore
from chronopersona.contracts.schemas import RetrievedContext


class MemoryNode:
    """Retrieves context from L1/L2 memory layers."""

    _VALID_INTENTS: frozenset[str] = frozenset({
        "retrieve",
        "vertical_generalize",
        "vertical_specify",
        "parallel_compare",
        "temporal_trace",
        "causal_explore",
        "empathize",
        "persona_switch",
    })

    def __init__(self, memory_store: AbstractMemoryStore) -> None:
        self._memory_store = memory_store

    def retrieve(self, query: str, branch_id: str, intent: Optional[str] = None) -> RetrievedContext:
        """Retrieve relevant memories for the given query."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if intent is not None and intent not in self._VALID_INTENTS:
            intent = "retrieve"
        return self._memory_store.retrieve(query, branch_id, intent=intent or "retrieve")
