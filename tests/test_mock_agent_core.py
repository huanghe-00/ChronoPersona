"""Unit tests for MockAgentCore."""

import pytest

from chronopersona.contracts.schemas import AgentOutput, EmbodiedState
from chronopersona.mocks import MockAgentCore


class TestMockAgentCore:
    """Tests for MockAgentCore."""

    def test_run_turn_returns_agent_output(self) -> None:
        """Normal path: run_turn returns AgentOutput with expected fields."""
        agent = MockAgentCore()
        out = agent.run_turn("Hello", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.reply_text
        assert out.branch_id == "main"

    def test_run_turn_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        agent = MockAgentCore()
        with pytest.raises(ValueError):
            agent.run_turn("hi", branch_id="")

    def test_switch_persona_updates_state(self) -> None:
        """switch_persona updates internal persona id."""
        agent = MockAgentCore()
        agent.switch_persona("therapist", branch_id="therapist")
        assert agent._persona_id == "therapist"
        assert agent._branch_id == "therapist"

    def test_switch_persona_empty_branch_raises(self) -> None:
        """switch_persona with empty branch_id raises ValueError."""
        agent = MockAgentCore()
        with pytest.raises(ValueError):
            agent.switch_persona("test", branch_id="")

    def test_get_emotion_state_returns_emotion_state(self) -> None:
        """get_emotion_state returns the current EmotionState."""
        agent = MockAgentCore()
        state = agent.get_emotion_state()
        assert state.current_state.value == "NEUTRAL"

    def test_get_memory_summary_returns_string(self) -> None:
        """get_memory_summary returns a non-empty string."""
        agent = MockAgentCore()
        summary = agent.get_memory_summary(branch_id="main")
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_get_memory_summary_empty_branch_raises(self) -> None:
        """get_memory_summary with empty branch_id raises ValueError."""
        agent = MockAgentCore()
        with pytest.raises(ValueError):
            agent.get_memory_summary(branch_id="")
