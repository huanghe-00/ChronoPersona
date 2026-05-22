"""A10: Action decision chain auditability evaluation."""

import pytest

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import EmotionLabel, EmotionState
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestA10ActionAuditable:
    """A10: Every action has non-empty reasoning and matches emotion state."""

    def test_action_plan_has_reasoning(self) -> None:
        """T01: ActionPlanner always produces reasoning."""
        planner = ActionPlanner()
        plan = planner.plan(
            "我慢慢靠近你",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert len(plan.reasoning) > 0

    def test_action_params_match_emotion_modulation(self) -> None:
        """T02: CONCERNED reduces speed_mult below NEUTRAL."""
        planner = ActionPlanner()
        plan_concerned = planner.plan(
            "让我靠近",
            EmotionState(current_state=EmotionLabel.CONCERNED, intensity=1.0),
            "main",
        )
        plan_neutral = planner.plan(
            "让我靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan_concerned.action_params["speed_mult"] < plan_neutral.action_params["speed_mult"]

    def test_end_to_end_action_plan_in_output(self) -> None:
        """T03: StateMachineAgentCore includes auditable ActionPlan in output."""
        from chronopersona.agent_core.action_planner import ActionPlanner

        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            action_planner=ActionPlanner(),
        )
        out = core.run_turn("慢慢靠近我", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.reasoning
        assert out.action_plan.action_token

    def test_idle_action_has_reasoning(self) -> None:
        """T04: Even default idle action carries reasoning."""
        planner = ActionPlanner()
        plan = planner.plan(
            "今天天气不错",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan.action_token == "idle"
        assert len(plan.reasoning) > 0
