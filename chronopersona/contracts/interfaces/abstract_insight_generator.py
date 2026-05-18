"""Abstract interface for periodic insight generation."""

from abc import ABC, abstractmethod
from typing import List

from chronopersona.contracts.schemas import Insight, MemoryEntry


class IInsightGenerator(ABC):
    """Periodic active reflection agent.

    Generates cross-session insights (patterns, trends, conflicts,
    recommendations) from recent episodic memories.
    """

    @abstractmethod
    def generate(
        self,
        branch_id: str,
        recent_memories: List[MemoryEntry],
    ) -> List[Insight]:
        """Generate insights from recent memories.

        Args:
            branch_id: Target branch.
            recent_memories: Memories since last generation.

        Returns:
            List of new insights.

        Raises:
            ValueError: If branch_id is empty.
        """

    @abstractmethod
    def should_trigger(self, branch_id: str, turn_count_since_last: int) -> bool:
        """Check if insight generation should trigger.

        Args:
            branch_id: Target branch.
            turn_count_since_last: Number of turns since last trigger.

        Returns:
            True if conditions met (e.g., >= 10 turns).
        """
