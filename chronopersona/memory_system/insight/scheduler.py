"""InsightScheduler implementation."""

from typing import Any, List

from loguru import logger


class InsightScheduler:
    """Trigger consolidation on turn-based and daily schedules."""

    def __init__(
        self,
        consolidation_agent: Any,
        trigger_rounds: int = 10,
    ) -> None:
        self._agent = consolidation_agent
        self._trigger_rounds = trigger_rounds
        self._last_trigger_turn: dict[str, int] = {}

    def maybe_trigger(self, branch_id: str, turn_count: int) -> List[Any]:
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

    def cleanup_expired(self, branch_id: str) -> int:
        # [FUTURE] Query L3 insights table for valid_until < now()
        return 0
