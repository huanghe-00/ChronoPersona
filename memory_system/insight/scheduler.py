"""Insight scheduler with Spindle Gating.

v0.7.0: Implements importance_score hard threshold (>= 0.7)
before memories enter the Insight processing queue.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger


# Spindle Gating threshold per requirements.md 4.14.1
SPINDLE_IMPORTANCE_THRESHOLD = 0.7


@dataclass
class InsightScheduleConfig:
    """Configuration for insight generation scheduling."""
    trigger_rounds: int = 10
    trigger_daily_hour: int = 3  # UTC
    min_confidence: float = 0.6
    spindle_threshold: float = SPINDLE_IMPORTANCE_THRESHOLD


class InsightScheduler:
    """Scheduler with Spindle Gating for memory consolidation.

    Only memories with importance_score >= spindle_threshold
    enter the processing queue. Others are marked as 'latent'.
    """

    def __init__(self, config: Optional[InsightScheduleConfig] = None) -> None:
        self._config = config or InsightScheduleConfig()
        self._round_count: int = 0
        self._last_daily_trigger: Optional[datetime] = None
        self._pending_queue: List[Dict[str, Any]] = []
        self._latent_memories: List[str] = []

    @property
    def config(self) -> InsightScheduleConfig:
        return self._config

    def should_trigger(self, current_time: Optional[datetime] = None) -> bool:
        """Check if insight generation should be triggered."""
        now = current_time or datetime.utcnow()
        self._round_count += 1

        # Round-based trigger
        if self._round_count >= self._config.trigger_rounds:
            self._round_count = 0
            logger.info("Insight trigger: round threshold reached")
            return True

        # Daily trigger
        if self._last_daily_trigger is None:
            self._last_daily_trigger = now
        elif now.hour >= self._config.trigger_daily_hour:
            if (now - self._last_daily_trigger) >= timedelta(hours=23):
                self._last_daily_trigger = now
                logger.info("Insight trigger: daily schedule")
                return True

        return False

    def enqueue_memories(self, memories: List[Dict[str, Any]]) -> int:
        """Apply Spindle Gating and enqueue qualifying memories.

        Returns number of memories that passed the gate.
        """
        passed = 0
        for mem in memories:
            importance = float(mem.get("importance", 0.0))
            if importance >= self._config.spindle_threshold:
                self._pending_queue.append(mem)
                passed += 1
                logger.debug(
                    "Spindle gate PASS: id={} importance={:.2f}",
                    mem.get("id", "unknown"),
                    importance,
                )
            else:
                mem_id = str(mem.get("id", "unknown"))
                self._latent_memories.append(mem_id)
                logger.debug(
                    "Spindle gate SKIP (latent): id={} importance={:.2f}",
                    mem_id,
                    importance,
                )

        logger.info(
            "Spindle gating: {} passed, {} latent out of {} total",
            passed,
            len(memories) - passed,
            len(memories),
        )
        return passed

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get pending memories for insight processing."""
        return list(self._pending_queue)

    def clear_pending(self) -> None:
        """Clear the pending queue after processing."""
        self._pending_queue.clear()

    def get_latent_count(self) -> int:
        """Get count of latent (skipped) memories."""
        return len(self._latent_memories)
