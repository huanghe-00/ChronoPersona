"""
Abstract interface for the memory store layer.

Defines the contract that any memory store implementation must satisfy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from chronopersona.contracts.schemas.agent import AgentOutput


class AbstractMemoryStore(ABC):
    """Abstract base class for the memory store.

    Implementations must support CRDT-based multi-device sync,
    MVCC branch isolation, and intent-driven retrieval.
    """

    @abstractmethod
    def add(self, memory: str, branch_id: str) -> str:
        """Add a memory entry to the store.

        Args:
            memory: The memory content to store.
            branch_id: The branch under which to store the memory.

        Returns:
            The unique identifier of the newly created memory entry.

        Raises:
            ValueError: If branch_id is invalid.
        """
        ...

    @abstractmethod
    def retrieve(self, query: str, branch_id: str, intent: str) -> List[str]:
        """Retrieve memories relevant to the query.

        Args:
            query: The search query.
            branch_id: The branch to search within.
            intent: The classified intent type (e.g. "temporal_trace").

        Returns:
            A list of memory content strings ordered by relevance.

        Raises:
            ValueError: If branch_id is invalid.
        """
        ...

    @abstractmethod
    def commit_version(self, branch_id: str) -> str:
        """Commit the current state as a new version.

        Args:
            branch_id: The branch to commit.

        Returns:
            The version identifier of the new commit.

        Raises:
            RuntimeError: If the commit operation fails.
        """
        ...

    @abstractmethod
    def checkout_branch(
        self, branch_id: str, version: Optional[str] = None
    ) -> None:
        """Switch to a specific branch and optionally a specific version.

        Args:
            branch_id: The branch to check out.
            version: Optional version identifier; if None, use the latest.

        Raises:
            ValueError: If branch_id or version is invalid.
        """
        ...

    @abstractmethod
    def get_facts(self, entity_id: str, branch_id: str) -> List[str]:
        """Retrieve facts associated with an entity.

        Args:
            entity_id: The entity identifier.
            branch_id: The branch to query.

        Returns:
            A list of fact strings.

        Raises:
            ValueError: If entity_id or branch_id is invalid.
        """
        ...

    @abstractmethod
    def link_entities(
        self, source: str, target: str, relation: str, branch_id: str
    ) -> bool:
        """Create a semantic link between two entities.

        Args:
            source: Source entity identifier.
            target: Target entity identifier.
            relation: The type of relation (e.g. "MENTIONS").
            branch_id: The branch under which to create the link.

        Returns:
            True if the link was successfully created.

        Raises:
            ValueError: If any argument is invalid.
        """
        ...
