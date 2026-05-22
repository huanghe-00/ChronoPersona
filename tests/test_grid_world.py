"""Unit tests for GridWorldAdapter."""

import math

import pytest

from chronopersona.contracts.schemas import SpatialRecord
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter


class TestGridWorldAdapter:
    """Tests for GridWorldAdapter perception, movement, and FOV."""

    def test_get_perception_returns_initial_state(self) -> None:
        """T01: New agent starts at origin with zero orientation."""
        adapter = GridWorldAdapter()
        percept = adapter.get_perception("agent-1")
        assert percept.agent_id == "agent-1"
        assert percept.x == 0.0
        assert percept.y == 0.0
        assert percept.theta == 0.0

    def test_get_perception_empty_agent_id_raises_valueerror(self) -> None:
        """T02: empty agent_id raises ValueError."""
        adapter = GridWorldAdapter()
        with pytest.raises(ValueError):
            adapter.get_perception("")

    def test_execute_action_updates_position(self) -> None:
        """T03: execute_action moves agent by delta coordinates."""
        adapter = GridWorldAdapter()
        adapter.execute_action(
            "agent-1", {"dx": 3.0, "dy": 4.0, "dtheta": math.pi / 2}
        )
        percept = adapter.get_perception("agent-1")
        assert percept.x == 3.0
        assert percept.y == 4.0

    def test_execute_action_clamps_to_grid_bounds(self) -> None:
        """T04: position is clamped within grid boundaries."""
        adapter = GridWorldAdapter(grid_width=10, grid_height=10)
        adapter.execute_action("agent-1", {"dx": 100.0, "dy": -50.0})
        percept = adapter.get_perception("agent-1")
        assert percept.x == 9.0
        assert percept.y == 0.0

    def test_add_object_and_fov_detection(self) -> None:
        """T05: Objects within FOV range appear in perception."""
        adapter = GridWorldAdapter(fov_range=5.0)
        adapter.add_object("agent-1", "tree", x=3.0, y=0.0)
        percept = adapter.get_perception("agent-1")
        assert "tree" in percept.fov_objects

    def test_fov_respects_range_limit(self) -> None:
        """T06: Objects beyond fov_range are excluded."""
        adapter = GridWorldAdapter(fov_range=2.0)
        adapter.add_object("agent-1", "far_tree", x=10.0, y=0.0)
        percept = adapter.get_perception("agent-1")
        assert "far_tree" not in percept.fov_objects

    def test_translate_action_token_approach(self) -> None:
        """T07: approach token translates to move_toward command."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "approach", {"target": "tree"}, "grid_2d"
        )
        assert cmd.command == "move_toward"
        assert cmd.params["target"] == "tree"

    def test_predict_action_idle_when_no_match(self) -> None:
        """T08: predict_action returns idle when no target matches task."""
        adapter = GridWorldAdapter()
        percept = adapter.get_perception("agent-1")
        action = adapter.predict_action(percept, "find something")
        assert action["action_token"] == "idle"

    def test_get_spatial_memory_returns_records(self) -> None:
        """T09: get_spatial_memory returns added spatial records."""
        adapter = GridWorldAdapter()
        adapter.add_object("agent-1", "rock", x=1.0, y=1.0)
        records = adapter.get_spatial_memory("agent-1")
        assert len(records) == 1
        assert isinstance(records[0], SpatialRecord)
        assert records[0].object_id == "rock"

    def test_approach_gently_grid_2d_params(self) -> None:
        """T10: approach_gently grid_2d includes scaled speed."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "approach_gently", {"speed": 1.0, "speed_mult": 0.5, "distance": 2.0}, "grid_2d"
        )
        assert cmd.command == "move_forward"
        assert cmd.params["speed"] == 0.5
        assert cmd.params["distance"] == 2.0

    def test_approach_gently_ros2_params(self) -> None:
        """T11: approach_gently ros2_mobile includes scaled linear velocity."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "approach_gently", {"speed": 0.5, "speed_mult": 0.5}, "ros2_mobile"
        )
        assert cmd.command == "cmd_vel"
        assert cmd.params["linear"] == 0.25
        assert cmd.params["angular"] == 0.0

    def test_unsupported_robot_type_raises(self) -> None:
        """T12: Unsupported robot_type raises ValueError."""
        adapter = GridWorldAdapter()
        with pytest.raises(ValueError):
            adapter.translate_action_token(
                "approach_gently", {}, "unsupported_type"
            )

    def test_retreat_slowly_grid_2d(self) -> None:
        """T13: retreat_slowly moves backward with scaled speed."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "retreat_slowly", {"speed": 1.0, "speed_mult": 0.5}, "grid_2d"
        )
        assert cmd.command == "move_backward"
        assert cmd.params["speed"] == 0.5

    def test_turn_to_user_ros2(self) -> None:
        """T14: turn_to_user navigates to target coordinates."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "turn_to_user", {"target_x": 3.0, "target_y": 4.0}, "ros2_mobile"
        )
        assert cmd.command == "navigate_to"
        assert cmd.params["target_x"] == 3.0

    def test_interact_grid_2d(self) -> None:
        """T15: interact targets specific object."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "interact", {"object_id": "fridge"}, "grid_2d"
        )
        assert cmd.command == "interact_with"
        assert cmd.params["object_id"] == "fridge"

    def test_look_around_grid_2d(self) -> None:
        """T16: look_around scans field of view."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "look_around", {"range": 10.0}, "grid_2d"
        )
        assert cmd.command == "scan_fov"
        assert cmd.params["range"] == 10.0
