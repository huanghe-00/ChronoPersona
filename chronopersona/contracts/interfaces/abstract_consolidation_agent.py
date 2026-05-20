"""Interface for Memory Consolidation Agent (Dreaming)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IConsolidationAgent(ABC):
    """Periodic active reflection agent that extracts behavioral patterns
    from episodic memories and crystallizes them into semantic rules.
    """

    @abstractmethod
    def should_trigger(self, branch_id: str) -> bool:
        """Return True if consolidation should run for this branch."""

    @abstractmethod
    def consolidate(self, branch_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Extract patterns from L2 and return candidate behavioral rules.

        Args:
            branch_id: Target branch.
            top_k: Number of high-importance memories to process.

        Returns:
            List of candidate rules (dicts with trigger/action/confidence).

        Raises:
            ValueError: If branch_id is empty.
        """
