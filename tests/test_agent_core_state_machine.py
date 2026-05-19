"""Tests for StateMachineAgentCore."""

import pytest

from chronopersona.agent_core import StateMachineAgentCore
from chronopersona.agent_core.intent_node import IntentNode
from chronopersona.contracts.schemas import AgentOutput
from chronopersona.mocks import MockMemoryStore, MockModelRouter


class TestStateMachineAgentCore:
    """Tests for StateMachineAgentCore."""

    def test_run_turn_returns_agent_output(self) -> None:
        """Full turn produces AgentOutput with reply text."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("hello world", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.reply_text
        assert out.branch_id == "main"

    def test_run_turn_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        with pytest.raises(ValueError):
            core.run_turn("hello", branch_id="")

    def test_switch_persona_updates_state(self) -> None:
        """switch_persona updates internal persona id."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core.switch_persona("therapist", branch_id="main")
        assert core._persona_id == "therapist"

    def test_get_memory_summary_returns_string(self) -> None:
        """get_memory_summary returns a formatted string."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        summary = core.get_memory_summary("main")
        assert isinstance(summary, str)
        assert "Working:" in summary


