"""Abstract interface for episodic memory store."""

from abc import ABC, abstractmethod
from typing import List, Optional

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext


class AbstractEpisodicStore(ABC):
    """Interface for L2 episodic memory storage."""

    @abstractmethod
    def add(self, entry: MemoryEntry, branch_id: str) -> str:
        """Add a memory entry and return its ID.

        ID handling contract:
        - If entry.id is empty or unset, the implementation generates
          a unique ID appropriate for the storage backend.
        - If entry.id is provided (e.g., for deterministic evaluation
          scenarios, MVO seed loading, or external data migration),
          the implementation MUST use it as-is and return it without
          modification.

        Args:
            entry: Memory entry to store.
            branch_id: Branch identifier. Must not be empty.

        Returns:
            The memory ID (generated or caller-provided).

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str,
        branch_id: str,
        top_k: int = 5,
        intent: Optional[str] = None,
    ) -> RetrievedContext:
        """Retrieve relevant memories for a query.

        Args:
            query: Search query text.
            branch_id: Branch identifier. Must not be empty.
            top_k: Maximum number of results.
            intent: Optional intent type for filtering.

        Returns:
            RetrievedContext with episodic memories.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def delete(self, memory_id: str, branch_id: str) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: ID of the memory to delete.
            branch_id: Branch identifier. Must not be empty.

        Returns:
            True if deletion succeeded.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
