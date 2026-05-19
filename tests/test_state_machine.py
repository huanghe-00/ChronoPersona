"""Unit tests for StateMachineAgentCore."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import AgentOutput, ChangeSet, EmotionState
from chronopersona.mocks import (
    MockMemoryStore,
    MockModelRouter,
    MockVersionManager,
)


class TestStateMachineAgentCore:
    """Tests for StateMachineAgentCore with mock dependencies."""

    def test_run_turn_returns_agent_output(self) -> None:
        """T01: run_turn returns AgentOutput with correct branch_id."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        out = agent.run_turn("Hello", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.branch_id == "main"
        assert out.reply_text

    def test_run_turn_empty_branch_raises_valueerror(self) -> None:
        """T02: run_turn with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        with pytest.raises(ValueError):
            agent.run_turn("hi", branch_id="")

    def test_switch_persona_updates_persona_id(self) -> None:
        """T03: switch_persona updates internal persona_id."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        agent.switch_persona("therapist", branch_id="main")
        assert agent._persona_id == "therapist"

    def test_switch_persona_empty_branch_raises_valueerror(self) -> None:
        """T04: switch_persona with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        with pytest.raises(ValueError):
            agent.switch_persona("therapist", branch_id="")

    def test_get_emotion_state_returns_emotion_state(self) -> None:
        """T05: get_emotion_state returns EmotionState."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        emotion = agent.get_emotion_state()
        assert isinstance(emotion, EmotionState)

    def test_get_memory_summary_returns_string(self) -> None:
        """T06: get_memory_summary returns descriptive string."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        summary = agent.get_memory_summary(branch_id="main")
        assert isinstance(summary, str)
        assert "Working:" in summary

    def test_get_memory_summary_empty_branch_raises_valueerror(self) -> None:
        """T07: get_memory_summary with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        with pytest.raises(ValueError):
            agent.get_memory_summary(branch_id="")

    def test_commit_session_snapshot_creates_version(self) -> None:
        """T08: commit_session_snapshot creates a Version via version_manager."""
        store = MockMemoryStore()
        router = MockModelRouter()
        vm = MockVersionManager()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
            version_manager=vm,
        )
        version = agent.commit_session_snapshot("main")
        assert version.branch_id == "main"
        assert "-v" in version.version

    def test_commit_session_snapshot_empty_branch_raises_valueerror(self) -> None:
        """T09: commit_session_snapshot with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        router = MockModelRouter()
        vm = MockVersionManager()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
            version_manager=vm,
        )
        with pytest.raises(ValueError):
            agent.commit_session_snapshot("")

    def test_commit_session_snapshot_no_version_manager_raises_runtimeerror(self) -> None:
        """T10: commit_session_snapshot without version_manager raises RuntimeError."""
        store = MockMemoryStore()
        router = MockModelRouter()
        agent = StateMachineAgentCore(
            memory_store=store,
            model_router=router,
        )
        with pytest.raises(RuntimeError):
            agent.commit_session_snapshot("main")
