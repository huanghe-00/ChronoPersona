"""Insight trigger scheduler using APScheduler."""

from __future__ import annotations

from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from chronopersona.contracts.interfaces import IInsightGenerator
from chronopersona.contracts.schemas import Insight, MemoryEntry


class InsightScheduler:
    """Periodic insight trigger with round-count and cron dual mode.

    Wraps APScheduler BackgroundScheduler for production-grade cron jobs.
    """

    def __init__(
        self,
        generator: IInsightGenerator,
        turn_threshold: int = 10,
    ) -> None:
        self._generator = generator
        self._turn_threshold = turn_threshold
        self._turn_counts: Dict[str, int] = {}
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self._daily_scan,
            trigger=CronTrigger(hour=3, minute=0),
            id="insight_daily",
            replace_existing=True,
        )
        self._scheduler.start()

    def on_turn_end(
        self,
        branch_id: str,
        recent_memories: List[MemoryEntry],
    ) -> List[Insight]:
        """Increment turn counter and trigger insight generation if threshold reached."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        self._turn_counts[branch_id] = self._turn_counts.get(branch_id, 0) + 1
        if self._turn_counts[branch_id] >= self._turn_threshold:
            self._turn_counts[branch_id] = 0
            return self._generator.generate(branch_id, recent_memories)
        return []

    def _daily_scan(self) -> None:
        """Daily forced scan regardless of turn count.

        TODO(W4+): Integrate with memory store to fetch recent_memories.
        """
        pass

    def shutdown(self) -> None:
        """Shutdown background scheduler."""
        self._scheduler.shutdown()
