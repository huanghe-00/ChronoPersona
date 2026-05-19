"""Unit tests for embodied adapter implementations."""

import pytest

from chronopersona.contracts.interfaces import AbstractEmbodiedAdapter
from chronopersona.contracts.schemas import EmbodiedState
from chronopersona.mocks.mock_embodied_adapter import MockEmbodiedAdapter


class TestMockEmbodiedAdapter:
    """Tests for MockEmbodiedAdapter ensuring AbstractEmbodiedAdapter compliance."""

    def test_get_perception_returns_embodied_state(self) -> None:
        """T01: get_perception returns EmbodiedState for valid agent_id."""
        adapter: AbstractEmbodiedAdapter = MockEmbodiedAdapter()
        percept = adapter.get_perception("agent-1")
        assert isinstance(percept, EmbodiedState)
        assert percept.agent_id == "agent-1"

    def test_get_perception_empty_agent_id_raises_valueerror(self) -> None:
        """T02: get_perception with empty agent_id raises ValueError."""
        adapter: AbstractEmbodiedAdapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.get_perception("")

    def test_translate_action_token_returns_command(self) -> None:
        """T03: translate_action_token returns LowLevelCommand."""
        adapter: AbstractEmbodiedAdapter = MockEmbodiedAdapter()
        cmd = adapter.translate_action_token("move", {"x": 1}, "grid_2d")
        assert cmd.robot_type == "grid_2d"
        assert "move" in cmd.command

    def test_translate_action_token_empty_args_raises_valueerror(self) -> None:
        """T04: translate_action_token with empty action_token or robot_type raises ValueError."""
        adapter: AbstractEmbodiedAdapter = MockEmbodiedAdapter()
        with pytest.raises(ValueError):
            adapter.translate_action_token("", {}, "grid_2d")
        with pytest.raises(ValueError):
            adapter.translate_action_token("move", {}, "")
