"""Unit tests for GridWorldAdapter."""

import math

import pytest

from chronopersona.contracts.schemas import EmbodiedState, LowLevelCommand
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter


class TestGridWorldAdapter:
    """Tests for GridWorldAdapter ensuring AbstractEmbodiedAdapter compliance."""

    def test_get_perception_returns_embodied_state(self) -> None:
        """T01: get_perception returns EmbodiedState for valid agent_id."""
        adapter = GridWorldAdapter()
        percept = adapter.get_perception("agent-1")
        assert isinstance(percept, EmbodiedState)
        assert percept.agent_id == "agent-1"
        assert percept.x == 0.0
        assert percept.y == 0.0

    def test_get_perception_empty_agent_id_raises_valueerror(self) -> None:
        """T02: get_perception with empty agent_id raises ValueError."""
        adapter = GridWorldAdapter()
        with pytest.raises(ValueError):
            adapter.get_perception("")

    def test_execute_action_moves_agent(self) -> None:
        """T03: execute_action updates agent position."""
        adapter = GridWorldAdapter()
        adapter.execute_action("agent-1", {"dx": 5.0, "dy": 3.0})
        percept = adapter.get_perception("agent-1")
        assert percept.x == 5.0
        assert percept.y == 3.0

    def test_execute_action_clamps_to_grid_bounds(self) -> None:
        """T04: execute_action clamps position to grid boundaries."""
        adapter = GridWorldAdapter(grid_width=10, grid_height=10)
        adapter.execute_action("agent-1", {"dx": 100.0, "dy": -100.0})
        percept = adapter.get_perception("agent-1")
        assert percept.x == 9.0
        assert percept.y == 0.0

    def test_translate_action_token_returns_command(self) -> None:
        """T05: translate_action_token returns LowLevelCommand."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token("move", {"x": 1}, "grid_2d")
        assert isinstance(cmd, LowLevelCommand)
        assert cmd.robot_type == "grid_2d"
        assert "move" in cmd.command

    def test_translate_action_token_empty_args_raises_valueerror(self) -> None:
        """T06: translate_action_token with empty action_token or robot_type raises ValueError."""
        adapter = GridWorldAdapter()
        with pytest.raises(ValueError):
            adapter.translate_action_token("", {}, "grid_2d")
        with pytest.raises(ValueError):
            adapter.translate_action_token("move", {}, "")

    def test_predict_action_returns_action_dict(self) -> None:
        """T07: predict_action returns a dict with action_token."""
        adapter = GridWorldAdapter()
        percept = adapter.get_perception("agent-1")
        action = adapter.predict_action(percept, "move to target")
        assert isinstance(action, dict)
        assert "action_token" in action

    def test_predict_action_empty_task_desc_raises_valueerror(self) -> None:
        """T08: predict_action with empty task_desc raises ValueError."""
        adapter = GridWorldAdapter()
        percept = adapter.get_perception("agent-1")
        with pytest.raises(ValueError):
            adapter.predict_action(percept, "")

    def test_get_spatial_memory_returns_list(self) -> None:
        """T09: get_spatial_memory returns list of SpatialRecord."""
        adapter = GridWorldAdapter()
        adapter.add_object("agent-1", "obj-1", 2.0, 3.0)
        records = adapter.get_spatial_memory("agent-1")
        assert len(records) == 1
        assert records[0].object_id == "obj-1"

    def test_fov_computation_includes_objects_in_cone(self) -> None:
        """T10: FOV computation includes objects within the field of view."""
        adapter = GridWorldAdapter(fov_angle_deg=90.0, fov_range=10.0)
        # Place agent at origin facing east (theta=0)
        adapter._agents["agent-1"] = (0.0, 0.0, 0.0)
        adapter.add_object("agent-1", "obj-visible", 5.0, 0.0)   # directly ahead
        adapter.add_object("agent-1", "obj-behind", -1.0, 0.0)   # behind
        percept = adapter.get_perception("agent-1")
        assert "obj-visible" in percept.fov_objects
        assert "obj-behind" not in percept.fov_objects
