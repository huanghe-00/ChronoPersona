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

    def test_emotion_state_has_confidence_field(self) -> None:
        """EmotionState includes confidence field with T0 rule values."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("我好焦虑", branch_id="main")
        es = out.emotion_state
        assert es.current_state.value == "CONCERNED"
        assert es.confidence == 0.9  # matched keyword -> high confidence

    def test_neutral_emotion_has_low_confidence(self) -> None:
        """Neutral fallback has reduced confidence."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("今天天气不错", branch_id="main")
        es = out.emotion_state
        assert es.current_state.value == "NEUTRAL"
        assert es.confidence == 0.5  # no keyword match -> low confidence

