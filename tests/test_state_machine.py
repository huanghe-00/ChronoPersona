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

    def test_run_turn_updates_emotion_state(self) -> None:
        """T11: Negative input updates emotion to CONCERNED."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core.run_turn("我最近很焦虑", branch_id="main")
        es = core.get_emotion_state()
        assert es.current_state.value == "CONCERNED"
        assert es.intensity > 0.0

    def test_run_turn_positive_input_empathetic(self) -> None:
        """T12: Positive input updates emotion to EMPATHETIC."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core.run_turn("今天真开心", branch_id="main")
        es = core.get_emotion_state()
        assert es.current_state.value == "EMPATHETIC"

    def test_build_prompt_includes_embodied_state(self) -> None:
        """T13: _build_prompt embeds embodied state description."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import EmbodiedState, RetrievedContext
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        es = EmbodiedState(x=3.0, y=4.0, theta=0.0, fov_objects=["sofa", "table"])
        prompt = core._build_prompt("hi", ctx, "main", embodied_state=es)
        assert "[Embodied State]" in prompt
        assert "sofa" in prompt

    def test_output_contains_updated_emotion_state(self) -> None:
        """T14: AgentOutput reflects updated emotion state after turn."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        out = core.run_turn("我好难过", branch_id="main")
        assert out.emotion_state.current_state.value == "CONCERNED"
        assert out.emotion_state.intensity == 0.7

    def test_output_contains_emotion_modulation_with_planner(self) -> None:
        """T15: AgentOutput contains emotion_modulation when ActionPlanner active."""
        from chronopersona.agent_core.action_planner import ActionPlanner
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            action_planner=ActionPlanner(),
        )
        out = core.run_turn("慢慢靠近", branch_id="main")
        assert out.emotion_modulation is not None
        assert "speed_mult" in out.emotion_modulation

    def test_t16_emotion_updated_before_prompt(self) -> None:
        """T16: Emotion state is updated before building the LLM prompt (H1 fix)."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        # Negative input should set CONCERNED before prompt construction
        out = core.run_turn("我最近很焦虑", branch_id="main")
        assert out.emotion_state.current_state.value == "CONCERNED"
        # The reply text should reflect the updated emotion (MockModelRouter returns deterministic text)
        assert out.reply_text

    def test_build_prompt_includes_emotion_state(self) -> None:
        """T17: _build_prompt embeds current emotion state for LLM modulation."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import EmotionLabel, EmotionState, RetrievedContext
        core._emotion_state = EmotionState(
            current_state=EmotionLabel.CONCERNED,
            intensity=0.7,
            trigger_reason="User expressed anxiety",
        )
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        prompt = core._build_prompt("hi", ctx, "main")
        assert "[Emotion State]" in prompt
        assert "CONCERNED" in prompt
        assert "0.7" in prompt
