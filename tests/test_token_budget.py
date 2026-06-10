"""Tests for hard token budget throttle (v1.1.0 production baseline)."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestTokenBudget:
    """Verify token budget fuse and accumulation behavior."""

    @pytest.fixture
    def core(self) -> StateMachineAgentCore:
        return StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )

    def test_budget_fuse_at_100_percent(self, core: StateMachineAgentCore) -> None:
        """T1: Budget exhausted → fixed fuse message, LLM skipped, no token increase."""
        core._tokens_used["main"] = 8000
        out = core.run_turn("你好", branch_id="main")
        assert "预算已用尽" in out.reply_text
        assert out.branch_id == "main"
        assert core._tokens_used["main"] == 8000

    def test_budget_accumulates_across_turns(self, core: StateMachineAgentCore) -> None:
        """T2: Token usage monotonically increases across turns."""
        core.run_turn("你好", branch_id="main")
        first_used = core._tokens_used["main"]
        assert first_used > 0

        core.run_turn("今天天气怎么样", branch_id="main")
        second_used = core._tokens_used["main"]
        assert second_used > first_used

    def test_budget_80_percent_still_services(self, core: StateMachineAgentCore) -> None:
        """T3: Below 100% budget, service continues and accumulates."""
        core._tokens_used["main"] = 7000
        out = core.run_turn("你好", branch_id="main")
        assert "预算已用尽" not in out.reply_text
        assert core._tokens_used["main"] > 7000
