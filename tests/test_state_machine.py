"""Unit tests for StateMachineAgentCore."""

from unittest.mock import MagicMock, patch

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import AgentOutput, MemoryEntry, Version
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter
from chronopersona.mocks.mock_version_manager import MockVersionManager


class TestStateMachineAgentCore:
    """Tests for StateMachineAgentCore orchestration and state management."""

    @patch("chronopersona.agent_core.state_machine.IntentNode")
    def test_run_turn_returns_agent_output(self, mock_intent_cls) -> None:
        """T01: Full turn pipeline returns AgentOutput with branch_id."""
        mock_intent_cls.return_value.classify.return_value = MagicMock(value="retrieve")

        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("Hello", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.branch_id == "main"
        assert "Hello" in out.reply_text

    def test_run_turn_empty_branch_raises_valueerror(self) -> None:
        """T02: Empty branch_id raises ValueError."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        with pytest.raises(ValueError):
            core.run_turn("hi", branch_id="")

    def test_switch_persona_commits_version(self) -> None:
        """T03: switch_persona commits a version snapshot when manager provided."""
        vm = MockVersionManager()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            version_manager=vm,
        )
        core.switch_persona("therapist", branch_id="main")
        assert len(vm.log("main")) == 1

    def test_switch_persona_with_injector(self) -> None:
        """T04: switch_persona ejects old persona and injects new one."""
        injector = MagicMock()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            persona_injector=injector,
        )
        core.switch_persona("rpg-hero", branch_id="main")
        injector.eject.assert_called_once_with("default", "main")
        injector.inject.assert_called_once_with("rpg-hero", "main", core)

    def test_get_memory_summary_returns_summary(self) -> None:
        """T05: get_memory_summary returns working and episodic counts."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="data"), branch_id="main")
        core = StateMachineAgentCore(
            memory_store=store,
            model_router=MockModelRouter(),
        )
        summary = core.get_memory_summary(branch_id="main")
        assert "Working:" in summary
        assert "Episodic:" in summary

    def test_commit_session_snapshot_returns_version(self) -> None:
        """T06: commit_session_snapshot delegates to version manager."""
        vm = MockVersionManager()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            version_manager=vm,
        )
        v = core.commit_session_snapshot(branch_id="main")
        assert isinstance(v, Version)
        assert v.branch_id == "main"

    def test_commit_session_snapshot_no_manager_raises(self) -> None:
        """T07: commit without version_manager raises RuntimeError."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        with pytest.raises(RuntimeError):
            core.commit_session_snapshot(branch_id="main")

    def test_working_memory_window_branch_isolation(self) -> None:
        """T08: WorkingMemoryWindow instances are isolated per branch."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        w1 = core._get_or_create_window("branch-a")
        w2 = core._get_or_create_window("branch-b")
        assert w1.branch_id == "branch-a"
        assert w2.branch_id == "branch-b"
        assert w1 is not w2
    def test_run_turn_with_action_planner(self) -> None:
        """T09: ActionPlanner produces action_plan in AgentOutput."""
        from chronopersona.agent_core.action_planner import ActionPlanner
        
        planner = ActionPlanner()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            action_planner=planner,
        )
        out = core.run_turn("慢慢靠近我", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.action_token == "approach_gently"

    def test_run_turn_without_action_planner(self) -> None:
        """T10: Without planner, action_plan is None."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("hello", branch_id="main")
        assert out.action_plan is None
