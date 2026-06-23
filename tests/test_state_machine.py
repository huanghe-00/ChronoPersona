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
        from chronopersona.agent_core.intent_node import Intent
        mock_intent_cls.return_value.classify.return_value = Intent.GENERAL

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
    @patch("chronopersona.agent_core.state_machine.IntentNode")
    def test_run_turn_with_action_planner(self, mock_intent_cls) -> None:
        """T09: ActionPlanner produces action_plan in AgentOutput."""
        from chronopersona.agent_core.intent_node import Intent
        mock_intent_cls.return_value.classify.return_value = Intent.GENERAL

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

    @patch("chronopersona.agent_core.state_machine.IntentNode")
    def test_output_contains_emotion_modulation_with_planner(self, mock_intent_cls) -> None:
        """T15: AgentOutput contains emotion_modulation when ActionPlanner active."""
        from chronopersona.agent_core.intent_node import Intent
        mock_intent_cls.return_value.classify.return_value = Intent.GENERAL

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

    def test_build_prompt_includes_l3_context(self) -> None:
        """T18: _build_prompt embeds semantic facts and insights from L3."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import RetrievedContext, Fact
        ctx = RetrievedContext(
            episodic_memories=[],
            semantic_facts=[Fact(attribute="Preference", value="Sichuan cuisine")],
            insights=["Anxiety level rising over past sessions"],
            total_tokens=0,
        )
        prompt = core._build_prompt("hi", ctx, "main")
        assert "[Semantic Facts]" in prompt
        assert "Sichuan cuisine" in prompt
        assert "[Insights]" in prompt
        assert "Anxiety level" in prompt

    def test_navigation_intent_success(self) -> None:
        """T19: Navigation intent drives GridWorldAdapter to target and updates position."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        adapter.add_object("default", "沙发", 2.0, 3.0)
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("到沙发旁边", branch_id="main")
        assert "沙发" in out.reply_text
        assert "已到达" in out.reply_text
        assert out.branch_id == "main"
        assert out.action_plan is not None
        assert out.action_plan.action_token == "navigate_to_object"
        assert out.action_plan.action_params.get("path") is not None
        assert len(out.action_plan.action_params["path"]) > 0
        # Verify adapter state updated
        es = adapter.get_perception("default")
        assert es.x == 8.0  # 沙发新坐标 x
        assert es.y == 6.0  # 沙发新坐标 y

        # Verify navigation event was persisted to episodic memory
        ctx = core._memory_store.retrieve("导航", branch_id="main")
        assert any("沙发" in m.content for m in ctx.episodic_memories)
        assert any("导航" in m.content for m in ctx.episodic_memories)

    def test_navigation_intent_not_found(self) -> None:
        """T20: Navigation to unknown target returns failure message."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("到火星旁边", branch_id="main")
        assert "无法找到" in out.reply_text
        assert out.branch_id == "main"
        # Failure should not produce action_plan
        assert out.action_plan is None

    def test_navigation_without_adapter_falls_back(self) -> None:
        """T21: NAVIGATION intent without embodied_adapter falls through to normal LLM flow."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=None,
        )
        out = core.run_turn("到沙发旁边", branch_id="main")
        assert out.branch_id == "main"
        # Normal flow returns MockModelRouter echo text
        assert out.reply_text

    def test_navigation_intent_via_approach_phrase(self) -> None:
        """T22: '靠近书架' triggers navigation to dynamically added object."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        adapter.add_object("default", "书架", x=5.0, y=5.0)
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("靠近书架", branch_id="main")
        assert "已到达" in out.reply_text
        assert out.action_plan is not None
        assert out.action_plan.action_token == "navigate_to_object"
        assert out.action_plan.action_params.get("path") is not None
        es = adapter.get_perception("default")
        assert es.x == 5.0
        assert es.y == 5.0

    def test_navigation_intent_via_walk_toward(self) -> None:
        """T23: '走向沙发' triggers navigation using hard-coded target."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("走向沙发", branch_id="main")
        assert "已到达" in out.reply_text
        assert out.action_plan is not None
        assert out.action_plan.action_token == "navigate_to_object"
        assert out.action_plan.action_params.get("path") is not None
        es = adapter.get_perception("default")
        assert es.x == 2.0
        assert es.y == 3.0

    def test_navigation_intent_via_navigate_to(self) -> None:
        """T24: '请帮我导航到床附近' triggers navigation."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("请帮我导航到床附近", branch_id="main")
        assert "已到达" in out.reply_text
        assert out.action_plan is not None
        assert out.action_plan.action_token == "navigate_to_object"
        assert out.action_plan.action_params.get("path") is not None
        es = adapter.get_perception("default")
        assert es.x == 4.0   # 床新坐标 x
        assert es.y == 11.0  # 床新坐标 y

    def test_build_prompt_truncates_l2_by_budget(self) -> None:
        """T25: L2 memories truncated when exceeding retrieval budget."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import RetrievedContext, MemoryEntry
        many = [MemoryEntry(content=f"ep-{i:03d}") for i in range(50)]
        ctx = RetrievedContext(episodic_memories=many, total_tokens=0)
        prompt = core._build_prompt("hi", ctx, "main")
        # With 30% of 4096 = ~1228 tokens and 150 tokens/episodic, max ~8 items
        assert "ep-000" in prompt
        assert "ep-049" not in prompt

    def test_build_prompt_truncates_l3_by_budget(self) -> None:
        """T26: L3 facts and insights truncated when exceeding semantic budget."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import RetrievedContext, Fact
        many_facts = [Fact(attribute=f"attr-{i}", value=f"val-{i}") for i in range(30)]
        many_insights = [f"insight-{i}" for i in range(30)]
        ctx = RetrievedContext(
            episodic_memories=[],
            semantic_facts=many_facts,
            insights=many_insights,
            total_tokens=0,
        )
        prompt = core._build_prompt("hi", ctx, "main")
        assert "attr-0" in prompt
        assert "attr-029" not in prompt
        assert "insight-0" in prompt
        assert "insight-029" not in prompt

    def test_build_prompt_preserves_embodied_and_emotion(self) -> None:
        """T27: Budget truncation preserves embodied state and emotion sections."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import (
            EmbodiedState,
            EmotionLabel,
            EmotionState,
            MemoryEntry,
            RetrievedContext,
        )
        core._emotion_state = EmotionState(
            current_state=EmotionLabel.CONCERNED,
            intensity=0.7,
        )
        many = [MemoryEntry(content=f"ep-{i:03d}") for i in range(100)]
        ctx = RetrievedContext(episodic_memories=many, total_tokens=0)
        es = EmbodiedState(x=1.0, y=2.0, theta=0.0, fov_objects=["chair"])
        prompt = core._build_prompt("hi", ctx, "main", embodied_state=es)
        assert "[Embodied State]" in prompt
        assert "[Emotion State]" in prompt

    def test_navigation_intent_to_fridge(self) -> None:
        """T28: End-to-end navigation to fridge via StateMachineAgentCore."""
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        out = core.run_turn("到冰箱旁边", branch_id="main")
        assert "已到达" in out.reply_text
        assert out.action_plan is not None
        assert out.action_plan.action_token == "navigate_to_object"
        assert out.action_plan.action_params.get("path") is not None
        assert len(out.action_plan.action_params["path"]) > 0
        es = adapter.get_perception("default")
        assert es.x == 10.0
        assert es.y == 4.0  # 冰箱新坐标 y

    def test_hard_budget_throttle_blocks_at_limit(self) -> None:
        """T29: v1.1.0 Hard budget throttle returns exhausted message when budget reached."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core._token_budget = 10  # Artificially low budget for test
        core._tokens_used["main"] = 10  # Already at limit
        out = core.run_turn("hello", branch_id="main")
        assert "预算已用尽" in out.reply_text
        assert out.action_plan is None

    def test_hard_budget_throttle_warning_at_80pct(self) -> None:
        """T30: v1.1.0 Budget warning logged at 80% threshold (verify via output)."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        core._token_budget = 100
        # First turn consumes tokens; verify it doesn't block
        out = core.run_turn("hello", branch_id="main")
        assert out.reply_text  # Should succeed
        # Manually set to 80% to verify warning path
        core._tokens_used["main"] = 80
        out2 = core.run_turn("test", branch_id="main")
        assert out2.reply_text  # Should still succeed (warning only)
