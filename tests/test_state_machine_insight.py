"""Integration test: StateMachineAgentCore + InsightScheduler."""

from unittest.mock import MagicMock

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import AgentOutput, EmotionState
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestStateMachineInsightScheduler:
    """Tests for InsightScheduler integration into AgentCore."""

    def test_scheduler_triggered_every_n_turns(self) -> None:
        """T01: InsightScheduler.maybe_trigger called after run_turn."""
        scheduler = MagicMock()
        scheduler.maybe_trigger.return_value = [{"insight": "x"}]

        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core.set_insight_scheduler(scheduler)

        core.run_turn("hello", branch_id="main")

        scheduler.maybe_trigger.assert_called_once()
        call_args = scheduler.maybe_trigger.call_args
        assert call_args[0][0] == "main"  # branch_id
        assert call_args[0][1] == 1       # turn_count

    def test_scheduler_not_called_when_not_attached(self) -> None:
        """T02: Without scheduler, run_turn completes normally."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("hello", branch_id="main")
        assert isinstance(out, AgentOutput)

    def test_turn_count_increments_per_branch(self) -> None:
        """T03: Turn counters are isolated per branch."""
        scheduler = MagicMock()
        scheduler.maybe_trigger.return_value = []

        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core.set_insight_scheduler(scheduler)

        core.run_turn("a", branch_id="branch-a")
        core.run_turn("b", branch_id="branch-a")
        core.run_turn("c", branch_id="branch-b")

        assert core._turn_count["branch-a"] == 2
        assert core._turn_count["branch-b"] == 1
