"""Abstract interface for L3 semantic memory (entity-fact-relationship store)."""

from abc import ABC, abstractmethod
from typing import List

from chronopersona.contracts.schemas import Fact


class AbstractSemanticStore(ABC):
    """Interface for L3 semantic memory storage.

    Manages structured facts and entity relationships with branch isolation.
    All operations require an explicit branch_id.
    """

    @abstractmethod
    def add_fact(self, fact: Fact, branch_id: str) -> None:
        """Store a structured fact.

        Args:
            fact: The fact to store.
            branch_id: Target branch.

        Raises:
            ValueError: If branch_id is empty.
        """

    @abstractmethod
    def get_facts(self, entity_id: str, branch_id: str) -> List[Fact]:
        """Retrieve facts for a given entity.

        Args:
            entity_id: Entity to look up.
            branch_id: Branch to query.

        Returns:
            List of matching facts.

        Raises:
            ValueError: If branch_id is empty.
        """

    @abstractmethod
    def link_entities(
        self,
        source: str,
        target: str,
        relation: str,
        branch_id: str,
    ) -> bool:
        """Create a relationship between two entities.

        Args:
            source: Source entity id.
            target: Target entity id.
            relation: Relationship type.
            branch_id: Target branch.

        Returns:
            True if the link was created or updated.

        Raises:
            ValueError: If branch_id is empty.
        """
