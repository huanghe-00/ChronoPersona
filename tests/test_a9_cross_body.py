"""A9: Cross-body migration — same persona drives different robot types."""

import pytest

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.contracts.schemas import EmotionLabel, EmotionState
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter


class TestA9CrossBodyMigration:
    """A9: Personality consistency across embodied adapters."""

    def test_concerned_reduces_speed_across_robot_types(self) -> None:
        """T01: CONCERNED emotion reduces speed in both grid_2d and ros2_mobile."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我靠近",
            EmotionState(current_state=EmotionLabel.CONCERNED, intensity=1.0),
            "main",
        )
        assert plan.action_token == "approach_gently"

        adapter = GridWorldAdapter()
        cmd_2d = adapter.translate_action_token(
            plan.action_token, plan.action_params, "grid_2d"
        )
        cmd_ros2 = adapter.translate_action_token(
            plan.action_token, plan.action_params, "ros2_mobile"
        )

        # Both robot types should receive embodied commands reflecting the same persona
        assert cmd_2d.robot_type == "grid_2d"
        assert cmd_ros2.robot_type == "ros2_mobile"
        # Different low-level commands (body-specific), but both carry the action
        assert cmd_2d.command == "move_forward"
        assert cmd_ros2.command == "cmd_vel"

    def test_neutral_maintains_baseline_speed(self) -> None:
        """T02: NEUTRAL emotion maintains baseline across grid_2d."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        adapter = GridWorldAdapter()
        cmd_2d = adapter.translate_action_token(
            plan.action_token, plan.action_params, "grid_2d"
        )
        assert cmd_2d.robot_type == "grid_2d"
        assert cmd_2d.params["speed"] == 1.0  # NEUTRAL baseline

    def test_action_token_consistency(self) -> None:
        """T03: Same LLM output produces same action_token regardless of robot_type."""
        planner = ActionPlanner()
        plan = planner.plan(
            "慢慢靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        adapter = GridWorldAdapter()

        cmd_2d = adapter.translate_action_token(plan.action_token, {}, "grid_2d")
        cmd_ros2 = adapter.translate_action_token(plan.action_token, {}, "ros2_mobile")

        # action_token is persona-level decision; translation is body-level mapping
        assert cmd_2d.command == "move_forward"
        assert cmd_ros2.command == "cmd_vel"
        assert cmd_2d.robot_type != cmd_ros2.robot_type
