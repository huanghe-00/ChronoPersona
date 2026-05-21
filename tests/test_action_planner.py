"""Unit tests for ActionPlanner."""

import pytest

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.contracts.interfaces import AbstractActionPlanner
from chronopersona.contracts.schemas import EmotionLabel, EmotionState
from chronopersona.mocks.mock_action_planner import MockActionPlanner


class TestActionPlanner:
    """Tests for real ActionPlanner."""

    def test_parse_approach_gently(self) -> None:
        """T01: Chinese '慢慢靠近' triggers approach_gently."""
        planner = ActionPlanner()
        plan = planner.plan(
            "我慢慢靠近你",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan.action_token == "approach_gently"
        assert "speed" in plan.action_params

    def test_concerned_reduces_speed(self) -> None:
        """T02: CONCERNED emotion reduces speed multiplier."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我靠近",
            EmotionState(current_state=EmotionLabel.CONCERNED, intensity=1.0),
            "main",
        )
        assert plan.action_params["speed_mult"] == 0.5

    def test_empty_branch_raises_valueerror(self) -> None:
        """T03: Empty branch_id raises ValueError."""
        planner = ActionPlanner()
        with pytest.raises(ValueError):
            planner.plan("test", EmotionState(current_state=EmotionLabel.NEUTRAL), "")

    def test_no_match_defaults_idle(self) -> None:
        """T04: No action pattern matched defaults to idle."""
        planner = ActionPlanner()
        plan = planner.plan(
            "今天天气不错",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan.action_token == "idle"

    def test_reasoning_non_empty(self) -> None:
        """T05: ActionPlan always contains reasoning."""
        planner = ActionPlanner()
        plan = planner.plan(
            "观察四周",
            EmotionState(current_state=EmotionLabel.CURIOUS, intensity=0.8),
            "main",
        )
        assert len(plan.reasoning) > 0


class TestMockActionPlanner:
    """Tests for MockActionPlanner."""

    def test_mock_is_instance(self) -> None:
        """T06: Mock is valid AbstractActionPlanner."""
        planner: AbstractActionPlanner = MockActionPlanner()
        assert isinstance(planner, AbstractActionPlanner)

    def test_mock_returns_fixed_plan(self) -> None:
        """T07: Mock returns predictable plan."""
        planner = MockActionPlanner()
        plan = planner.plan("x", EmotionState(current_state=EmotionLabel.NEUTRAL), "main")
        assert plan.action_token == "mock_action"
