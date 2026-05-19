"""Unit tests for agent core implementations."""

import pytest

from chronopersona.contracts.interfaces import AbstractAgentCore
from chronopersona.contracts.schemas import AgentOutput, EmotionState
from chronopersona.mocks.mock_agent_core import MockAgentCore


class TestMockAgentCore:
    """Tests for MockAgentCore ensuring AbstractAgentCore compliance."""

    def test_run_turn_returns_agent_output(self) -> None:
        """T01: run_turn returns AgentOutput with correct branch_id."""
        agent: AbstractAgentCore = MockAgentCore()
        out = agent.run_turn("Hello", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.branch_id == "main"
        assert "[Mock] Echo: Hello" in out.reply_text

    def test_run_turn_empty_branch_raises_valueerror(self) -> None:
        """T02: run_turn with empty branch_id raises ValueError."""
        agent: AbstractAgentCore = MockAgentCore()
        with pytest.raises(ValueError):
            agent.run_turn("hi", branch_id="")

    def test_switch_persona_updates_state(self) -> None:
        """T03: switch_persona updates internal persona_id."""
        agent: AbstractAgentCore = MockAgentCore()
        agent.switch_persona("therapist", branch_id="main")
        assert agent._persona_id == "therapist"

    def test_switch_persona_empty_branch_raises_valueerror(self) -> None:
        """T04: switch_persona with empty branch_id raises ValueError."""
        agent: AbstractAgentCore = MockAgentCore()
        with pytest.raises(ValueError):
            agent.switch_persona("therapist", branch_id="")

    def test_get_emotion_state_returns_emotion_state(self) -> None:
        """T05: get_emotion_state returns EmotionState."""
        agent: AbstractAgentCore = MockAgentCore()
        emotion = agent.get_emotion_state()
        assert isinstance(emotion, EmotionState)

    def test_get_memory_summary_returns_string(self) -> None:
        """T06: get_memory_summary returns descriptive string."""
        agent: AbstractAgentCore = MockAgentCore()
        summary = agent.get_memory_summary(branch_id="main")
        assert isinstance(summary, str)
        assert "main" in summary

    def test_get_memory_summary_empty_branch_raises_valueerror(self) -> None:
        """T07: get_memory_summary with empty branch_id raises ValueError."""
        agent: AbstractAgentCore = MockAgentCore()
        with pytest.raises(ValueError):
            agent.get_memory_summary(branch_id="")
