"""A9: Cross-body migration — same persona drives different robot types."""

import pytest

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.contracts.schemas import EmotionLabel, EmotionState
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter


class TestA9CrossBodyMigration:
    """A9: Personality consistency across embodied adapters."""

    def test_concerned_reduces_speed_across_robot_types(self) -> None:
        """T01: CONCERNED emotion reduces speed_mult; cross-body types differ."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我慢慢靠近",
            EmotionState(current_state=EmotionLabel.CONCERNED, intensity=1.0),
            "main",
        )
        assert plan.action_token == "approach_gently"
        assert plan.action_params["speed_mult"] == 0.5

        adapter = GridWorldAdapter()
        cmd_2d = adapter.translate_action_token(
            plan.action_token, plan.action_params, "grid_2d"
        )
        cmd_ros2 = adapter.translate_action_token(
            plan.action_token, plan.action_params, "ros2_mobile"
        )

        assert cmd_2d.robot_type == "grid_2d"
        assert cmd_ros2.robot_type == "ros2_mobile"
        assert cmd_2d.command != cmd_ros2.command

    def test_neutral_maintains_baseline_speed(self) -> None:
        """T02: NEUTRAL emotion maintains baseline speed_mult at planner level."""
        planner = ActionPlanner()
        plan = planner.plan(
            "让我慢慢靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        assert plan.action_token == "approach_gently"
        assert plan.action_params["speed_mult"] == 1.0  # NEUTRAL baseline: no reduction

    def test_action_token_consistency(self) -> None:
        """T03: Same action_token produces different commands per robot_type."""
        planner = ActionPlanner()
        plan = planner.plan(
            "慢慢靠近",
            EmotionState(current_state=EmotionLabel.NEUTRAL, intensity=0.5),
            "main",
        )
        adapter = GridWorldAdapter()

        cmd_2d = adapter.translate_action_token(
            plan.action_token, plan.action_params, "grid_2d"
        )
        cmd_ros2 = adapter.translate_action_token(
            plan.action_token, plan.action_params, "ros2_mobile"
        )

        assert cmd_2d.robot_type == "grid_2d"
        assert cmd_ros2.robot_type == "ros2_mobile"
        assert cmd_2d.command != cmd_ros2.command
        assert cmd_2d.command  # non-empty
        assert cmd_ros2.command  # non-empty
