"""Abstract interface for the memory store layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from chronopersona.contracts.schemas.base import Fact, MemoryEntry, RetrievedContext
from chronopersona.contracts.schemas.version import Snapshot, Version


class AbstractMemoryStore(ABC):
    """Abstract base class for the memory store.

    Implementations must support CRDT-based multi-device sync,
    MVCC branch isolation, and intent-driven retrieval.
    All operations require an explicit branch_id.
    """

    @abstractmethod
    def add(self, memory: MemoryEntry, branch_id: str) -> str:
        """Add a memory entry to the store.

        Args:
            memory: The memory entry to persist.
            branch_id: The branch under which to store the memory.
                Must not be empty.

        Returns:
            The unique identifier of the newly created memory entry.

        Raises:
            ValueError: If branch_id is empty or invalid.
            TypeError: If memory is not a MemoryEntry instance.
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str,
        branch_id: str,
        intent: Optional[str] = None,
    ) -> RetrievedContext:
        """Retrieve memories relevant to the query.

        Args:
            query: The search query.
            branch_id: The branch to search within. Must not be empty.
            intent: Optional intent type to guide retrieval strategy.

        Returns:
            Assembled context from L1/L2/L3/insights.

        Raises:
            ValueError: If branch_id is empty.
            PermissionError: If the caller lacks access to branch_id.
        """
        ...

    @abstractmethod
    def commit_version(self, branch_id: str) -> Version:
        """Commit the current state as a new version.

        Args:
            branch_id: The branch to commit. Must not be empty.

        Returns:
            Version metadata including timestamp and vector clock.

        Raises:
            ValueError: If branch_id is empty.
            RuntimeError: If the commit operation fails.
        """
        ...

    @abstractmethod
    def checkout_branch(
        self,
        branch_id: str,
        version: Optional[str] = None,
    ) -> Snapshot:
        """Switch to a specific branch and optionally a specific version.

        Args:
            branch_id: The branch to check out. Must not be empty.
            version: Optional version hash. If None, checks out latest.

        Returns:
            Snapshot containing the full branch state.

        Raises:
            ValueError: If branch_id is empty.
            LookupError: If branch or version does not exist.
        """
        ...

    @abstractmethod
    def get_facts(self, entity_id: str, branch_id: str) -> List[Fact]:
        """Retrieve facts associated with an entity.

        Args:
            entity_id: The entity identifier.
            branch_id: The branch to query. Must not be empty.

        Returns:
            List of facts associated with the entity.

        Raises:
            ValueError: If entity_id or branch_id is empty.
        """
        ...

    @abstractmethod
    def link_entities(
        self,
        source: str,
        target: str,
        relation: str,
        branch_id: str,
    ) -> bool:
        """Create a semantic link between two entities.

        Args:
            source: Source entity identifier.
            target: Target entity identifier.
            relation: The type of relation (e.g. "MENTIONS").
            branch_id: The branch under which to create the link.
                Must not be empty.

        Returns:
            True if the link was successfully created.

        Raises:
            ValueError: If any argument is invalid or empty.
            RuntimeError: If the underlying storage operation fails.
        """
        ...
