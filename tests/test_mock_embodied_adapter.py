"""Unit tests for MockEmbodiedAdapter."""

import pytest

from chronopersona.contracts.schemas import (
    EmbodiedState,
    LowLevelCommand,
    PerceptionResult,
    SpatialRecord,
)
from chronopersona.mocks import MockEmbodiedAdapter


class TestMockEmbodiedAdapter:
    """Tests for MockEmbodiedAdapter."""

    def test_get_perception_returns_embodied_state(self) -> None:
        """Normal path: get_perception returns EmbodiedState with correct agent_id."""
        adapter = MockEmbodiedAdapter()
        state = adapter.get_perception("agent-1")
        assert isinstance(state, EmbodiedState)
        assert state.agent_id == "agent-1"

    def test_get_perception_empty_agent_raises(self) -> None:
        """Empty agent_id raises ValueError."""
        adapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.get_perception("")

    def test_execute_action_returns_perception_result(self) -> None:
        """execute_action returns PerceptionResult with success=True."""
        adapter = MockEmbodiedAdapter()
        result = adapter.execute_action("agent-1", {"move": "forward"})
        assert isinstance(result, PerceptionResult)
        assert result.success is True

    def test_execute_action_empty_agent_raises(self) -> None:
        """execute_action with empty agent_id raises ValueError."""
        adapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.execute_action("", {"move": "forward"})

    def test_get_spatial_memory_returns_list(self) -> None:
        """get_spatial_memory returns a list of SpatialRecord."""
        adapter = MockEmbodiedAdapter()
        records = adapter.get_spatial_memory("agent-1")
        assert isinstance(records, list)
        # Mock returns empty list
        assert records == []

    def test_get_spatial_memory_empty_agent_raises(self) -> None:
        """get_spatial_memory with empty agent_id raises ValueError."""
        adapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.get_spatial_memory("")

    def test_predict_action_returns_dict(self) -> None:
        """predict_action returns a dict with action_token."""
        adapter = MockEmbodiedAdapter()
        percept = EmbodiedState(agent_id="agent-1")
        result = adapter.predict_action(percept, "navigate")
        assert isinstance(result, dict)
        assert result["action_token"] == "mock_action"

    def test_predict_action_empty_task_raises(self) -> None:
        """predict_action with empty task_desc raises ValueError."""
        adapter = MockEmbodiedAdapter()
        percept = EmbodiedState(agent_id="agent-1")
        with pytest.raises(ValueError):
            adapter.predict_action(percept, "")

    def test_translate_action_token_returns_low_level_command(self) -> None:
        """translate_action_token returns LowLevelCommand with correct fields."""
        adapter = MockEmbodiedAdapter()
        cmd = adapter.translate_action_token("move", {"speed": 1.0}, "grid_2d")
        assert isinstance(cmd, LowLevelCommand)
        assert cmd.robot_type == "grid_2d"
        assert cmd.command == "mock_move"
        assert cmd.params == {"speed": 1.0}

    def test_translate_action_token_empty_args_raises(self) -> None:
        """translate_action_token with empty action_token or robot_type raises ValueError."""
        adapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.translate_action_token("", {}, "grid_2d")
        with pytest.raises(ValueError):
            adapter.translate_action_token("move", {}, "")
