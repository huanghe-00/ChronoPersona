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

    def test_arousal_increases_speed_reduces_proximity(self) -> None:
        """T09: High arousal increases speed and reduces proximity."""
        planner = ActionPlanner()
        plan = planner.plan(
            "慢慢靠近",
            EmotionState(
                current_state=EmotionLabel.CONCERNED,
                intensity=1.0,
                arousal=0.75,
                valence=0.0,
            ),
            "main",
        )
        # CONCERNED base: speed_mult=0.5, proximity_mult=0.5
        # arousal=0.75: factor = 1.0 + (0.75 - 0.5) * 0.4 = 1.1
        # speed_mult = 0.5 * 1.1 = 0.55
        # proximity_mult = 0.5 * (1.0 - (0.75 - 0.5) * 0.3) = 0.4625
        assert plan.action_params["speed_mult"] == pytest.approx(0.55, rel=1e-3)
        assert plan.action_params["proximity_mult"] == pytest.approx(0.4625, rel=1e-3)

    def test_positive_valence_increases_volume(self) -> None:
        """T10: Positive valence increases volume multiplier (with intensity scaling)."""
        planner = ActionPlanner()
        plan = planner.plan(
            "观察四周",
            EmotionState(
                current_state=EmotionLabel.EMPATHETIC,
                intensity=0.5,
                arousal=0.0,
                valence=0.6,
            ),
            "main",
        )
        # EMPATHETIC base: volume_mult=0.9
        # intensity=0.5 scales base: 0.9 * 0.5 = 0.45
        # valence=0.6: 0.45 * (1.0 + 0.6 * 0.1) = 0.477
        assert plan.action_params["volume_mult"] == pytest.approx(0.477, rel=1e-3)

    def test_negative_valence_decreases_volume(self) -> None:
        """T11: Negative valence decreases volume multiplier (with intensity scaling)."""
        planner = ActionPlanner()
        plan = planner.plan(
            "后退",
            EmotionState(
                current_state=EmotionLabel.CONCERNED,
                intensity=0.5,
                arousal=0.0,
                valence=-0.5,
            ),
            "main",
        )
        # CONCERNED base: volume_mult=0.8
        # intensity=0.5 scales base: 0.8 * 0.5 = 0.4
        # valence=-0.5: 0.4 * (1.0 + (-0.5) * 0.15) = 0.37
        assert plan.action_params["volume_mult"] == pytest.approx(0.37, rel=1e-3)


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

    def test_parse_navigate_to_object(self) -> None:
        """T08: Chinese navigation phrase triggers navigate_to_object with target extraction."""
        planner = ActionPlanner()
        plan = planner.plan(
            "请移动到沙发旁边",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan.action_token == "navigate_to_object"
        assert plan.action_params.get("target") == "沙发"
        assert "nav target=沙发" in plan.reasoning
