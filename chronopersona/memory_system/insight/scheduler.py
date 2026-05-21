"""InsightScheduler implementation."""

from typing import Any, Dict, List

from loguru import logger


class InsightScheduler:
    """Trigger consolidation on turn-based and daily schedules."""

    def __init__(
        self,
        consolidation_agent: Any,
        trigger_rounds: int = 10,
        turn_threshold: int | None = None,
    ) -> None:
        self._agent = consolidation_agent
        self._trigger_rounds = (
            turn_threshold if turn_threshold is not None else trigger_rounds
        )
        self._last_trigger_turn: Dict[str, int] = {}
        self._turn_counts: Dict[str, int] = {}

    def on_turn_end(self, branch_id: str, memories: Any) -> List[Any]:
        """Increment turn counter and maybe trigger consolidation.

        Args:
            branch_id: Target branch.
            memories: Memories from the completed turn (unused in MVA).

        Raises:
            ValueError: If branch_id is empty.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._turn_counts[branch_id] = self._turn_counts.get(branch_id, 0) + 1
        return self.maybe_trigger(branch_id, self._turn_counts[branch_id])

    def maybe_trigger(self, branch_id: str, turn_count: int) -> List[Any]:
        """Evaluate trigger conditions and run consolidation if met."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        last = self._last_trigger_turn.get(branch_id, 0)
        if turn_count - last < self._trigger_rounds:
            return []

        if not self._agent.should_trigger(branch_id):
            return []

        logger.info(
            "InsightScheduler: triggering consolidation for {} at turn {}",
            branch_id,
            turn_count,
        )
        self._last_trigger_turn[branch_id] = turn_count
        return self._agent.consolidate(branch_id, top_k=10)

    def shutdown(self) -> None:
        """Graceful shutdown hook. MVA: no-op."""
        logger.info("InsightScheduler: shutdown")

    def cleanup_expired(self, branch_id: str) -> int:
        """Remove insights past their valid_until."""
        return 0
