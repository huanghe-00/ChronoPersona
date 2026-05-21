"""Tests for InsightScheduler."""

from unittest.mock import MagicMock

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.memory_system.insight import InsightScheduler


class TestInsightScheduler:
    """Tests for periodic insight trigger scheduler."""

    def test_turn_trigger_fires_at_threshold(self) -> None:
        """Trigger fires when turn count reaches threshold."""
        gen = MagicMock()
        gen.should_trigger.return_value = True
        gen.consolidate.return_value = [{"rule": "r1"}]

        sched = InsightScheduler(gen, turn_threshold=3)
        try:
            memories = [MemoryEntry(content="test")]
            assert sched.on_turn_end("main", memories) == []
            assert sched.on_turn_end("main", memories) == []
            insights = sched.on_turn_end("main", memories)
            assert len(insights) == 1
            assert insights[0]["rule"] == "r1"
        finally:
            sched.shutdown()

    def test_turn_trigger_not_fired_before_threshold(self) -> None:
        """No trigger before threshold."""
        gen = MagicMock()
        gen.should_trigger.return_value = True
        gen.consolidate.return_value = [{"rule": "r1"}]

        sched = InsightScheduler(gen, turn_threshold=5)
        try:
            memories = [MemoryEntry(content="x")]
            for _ in range(4):
                assert sched.on_turn_end("main", memories) == []
        finally:
            sched.shutdown()

    def test_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        gen = MagicMock()
        sched = InsightScheduler(gen)
        try:
            with pytest.raises(ValueError):
                sched.on_turn_end("", [MemoryEntry(content="test")])
        finally:
            sched.shutdown()

    def test_branch_isolation(self) -> None:
        """Turn counts are isolated by branch."""
        gen = MagicMock()
        gen.should_trigger.return_value = True
        gen.consolidate.return_value = [{"rule": "x"}]

        sched = InsightScheduler(gen, turn_threshold=2)
        try:
            memories = [MemoryEntry(content="test")]
            sched.on_turn_end("b1", memories)
            assert sched.on_turn_end("b2", memories) == []
            insights = sched.on_turn_end("b1", memories)
            assert len(insights) == 1
            assert insights[0]["rule"] == "x"
        finally:
            sched.shutdown()
