"""Unit tests for GridWorldAdapter."""

import math

import pytest

from chronopersona.embodied import GridWorldAdapter
from chronopersona.contracts.schemas import EmbodiedState, LowLevelCommand


class TestGridWorldAdapter:
    """Tests for GridWorldAdapter."""

    def test_get_perception_initial_state(self) -> None:
        """Initial perception returns zero coordinates and empty FOV."""
        adapter = GridWorldAdapter()
        state = adapter.get_perception("agent1")
        assert isinstance(state, EmbodiedState)
        assert state.agent_id == "agent1"
        assert state.x == 0.0
        assert state.y == 0.0
        assert state.theta == 0.0
        assert state.fov_objects == []

    def test_execute_action_moves_agent(self) -> None:
        """Execute action updates agent position."""
        adapter = GridWorldAdapter()
        adapter.execute_action("agent1", {"dx": 5.0, "dy": 3.0})
        state = adapter.get_perception("agent1")
        assert state.x == 5.0
        assert state.y == 3.0

    def test_fov_includes_nearby_object(self) -> None:
        """Object within FOV range and angle is visible."""
        adapter = GridWorldAdapter(fov_angle_deg=90.0, fov_range=10.0)
        adapter.add_object("agent1", "obj1", 5.0, 0.0)
        state = adapter.get_perception("agent1")
        assert "obj1" in state.fov_objects

    def test_fov_excludes_far_object(self) -> None:
        """Object beyond FOV range is not visible."""
        adapter = GridWorldAdapter(fov_range=5.0)
        adapter.add_object("agent1", "obj2", 10.0, 0.0)
        state = adapter.get_perception("agent1")
        assert "obj2" not in state.fov_objects

    def test_translate_action_token_approach(self) -> None:
        """Approach action token translates to move_toward command."""
        adapter = GridWorldAdapter()
        cmd = adapter.translate_action_token(
            "approach", {"target": "obj1"}, "grid_2d"
        )
        assert isinstance(cmd, LowLevelCommand)
        assert cmd.robot_type == "grid_2d"
        assert cmd.command == "move_toward"
        assert cmd.params["target"] == "obj1"

    def test_empty_agent_id_raises(self) -> None:
        """Empty agent_id raises ValueError."""
        adapter = GridWorldAdapter()
        with pytest.raises(ValueError):
            adapter.get_perception("")
        with pytest.raises(ValueError):
            adapter.execute_action("", {"dx": 1.0})
