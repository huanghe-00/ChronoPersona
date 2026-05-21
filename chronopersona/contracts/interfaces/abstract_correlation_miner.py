"""Abstract interface for correlation mining."""

from abc import ABC, abstractmethod
from typing import List, Optional

from chronopersona.contracts.schemas import MemoryEntry


class ICorrelationMiner(ABC):
    """Mine weak correlations between episodic memories."""

    @abstractmethod
    def mine_correlations(
        self,
        memories: List[MemoryEntry],
        branch_id: str,
        min_confidence: float = 0.6,
    ) -> List[str]:
        """Return list of correlated memory IDs.

        Args:
            memories: Episodic memories to analyze.
            branch_id: Branch context.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of memory IDs that are correlated.
        """
        ...

    @abstractmethod
    def get_correlation_score(
        self,
        memory_a: MemoryEntry,
        memory_b: MemoryEntry,
        branch_id: str,
    ) -> float:
        """Compute correlation score between two memories.

        Args:
            memory_a: First memory.
            memory_b: Second memory.
            branch_id: Branch context.

        Returns:
            Correlation score in [0, 1].
        """
        ...
