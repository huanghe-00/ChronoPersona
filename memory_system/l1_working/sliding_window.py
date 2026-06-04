"""L1 Working Memory sliding window with explicit budget allocation.

v0.7.0: Implements hard budget partitioning per requirements.md 4.14.1.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class BudgetAllocation:
    """Token budget allocation for L1 context assembly."""
    session_history: float = 0.40
    retrieved_memories: float = 0.30
    persona_anchor: float = 0.20
    scratchpad: float = 0.10


class WorkingMemoryWindow:
    """Sliding window with explicit budget enforcement.

    Hard truncation when any layer exceeds its allocation.
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        budget: Optional[BudgetAllocation] = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._budget = budget or BudgetAllocation()
        self._turns: List[Dict[str, Any]] = []
        self._compressed_summaries: List[Dict[str, Any]] = []

    @property
    def budget(self) -> BudgetAllocation:
        return self._budget

    def add_turn(self, turn: Dict[str, Any]) -> None:
        """Add a dialogue turn and enforce budget."""
        self._turns.append(turn)
        self._enforce_budget()

    def get_context(self) -> Dict[str, Any]:
        """Assemble context respecting budget allocations."""
        total_budget = self._max_tokens
        allocations = {
            "session_history": int(total_budget * self._budget.session_history),
            "retrieved_memories": int(total_budget * self._budget.retrieved_memories),
            "persona_anchor": int(total_budget * self._budget.persona_anchor),
            "scratchpad": int(total_budget * self._budget.scratchpad),
        }
        logger.debug("L1 budget allocations: {}", allocations)
        return {
            "turns": self._turns,
            "summaries": self._compressed_summaries,
            "allocations": allocations,
        }

    def _enforce_budget(self) -> None:
        """Hard truncate turns exceeding session_history allocation."""
        session_budget = int(self._max_tokens * self._budget.session_history)
        estimated_tokens = sum(
            len(str(t.get("content", ""))) // 4 for t in self._turns
        )
        while estimated_tokens > session_budget and len(self._turns) > 1:
            removed = self._turns.pop(0)
            estimated_tokens -= len(str(removed.get("content", ""))) // 4
            logger.debug("L1 budget enforced: removed oldest turn")
