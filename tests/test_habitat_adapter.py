"""Contract tests for HabitatAdapter.

Validates that HabitatAdapter correctly implements the
AbstractEmbodiedAdapter contract, including 3D navigation
and visual observation methods.

NOTE: Full simulator integration tests require habitat-sim installed;
these contract tests validate interface compliance and error handling
without the simulator.
"""

import pytest

from chronopersona.contracts.schemas import (
    EmbodiedState,
    LowLevelCommand,
    NavigationResult,
    PerceptionResult,
    RobotState3D,
    SemanticNavigationGoal,
    SpatialRecord,
    VisualObservation,
)
from chronopersona.embodied.habitat_adapter import HabitatAdapter


class TestHabitatAdapterContract:
    """Verify HabitatAdapter satisfies AbstractEmbodiedAdapter contract."""

    def setup_method(self) -> None:
        self.adapter = HabitatAdapter(scene_path="", agent_id="test_agent")

    def test_2d_get_perception_raises(self):
        """2D get_perception must raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="2D EmbodiedState"):
            self.adapter.get_perception("test_agent")

    def test_2d_execute_action_raises(self):
        """2D execute_action must raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="2D action execution"):
            self.adapter.execute_action("test_agent", {})

    def test_2d_predict_action_raises(self):
        """2D predict_action must raise NotImplementedError."""
        state = EmbodiedState(agent_id="test_agent")
        with pytest.raises(NotImplementedError, match="2D predict_action"):
            self.adapter.predict_action(state, "go to sofa")

    def test_2d_translate_action_token_raises(self):
        """2D translate_action_token must raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="2D action token"):
            self.adapter.translate_action_token("move", {}, "grid_2d")

    def test_get_spatial_memory_empty_agent_id_raises(self):
        """Empty agent_id must raise ValueError."""
        with pytest.raises(ValueError, match="agent_id must not be empty"):
            self.adapter.get_spatial_memory("")

    def test_get_spatial_memory_returns_list(self):
        """Valid agent_id returns list (empty for new agent)."""
        records = self.adapter.get_spatial_memory("test_agent")
        assert isinstance(records, list)

    def test_get_visual_observation_requires_sim(self):
        """get_visual_observation raises without simulator."""
        with pytest.raises(NotImplementedError):
            self.adapter.get_visual_observation()

    def test_get_robot_state_3d_requires_sim(self):
        """get_robot_state_3d raises without simulator."""
        with pytest.raises(NotImplementedError):
            self.adapter.get_robot_state_3d()

    def test_navigate_empty_target_raises(self):
        """navigate_to_object with empty target must raise ValueError."""
        with pytest.raises(ValueError, match="target_object must not be empty"):
            self.adapter.navigate_to_object(SemanticNavigationGoal(target_object=""))

    def test_navigate_unknown_target_returns_failure(self):
        """Unknown target object returns failed NavigationResult."""
        result = self.adapter.navigate_to_object(
            SemanticNavigationGoal(target_object="未知物体")
        )
        assert isinstance(result, NavigationResult)
        assert result.success is False
        assert result.steps_taken == 0

    def test_navigate_known_target_requires_sim(self):
        """Known target requires simulator; raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.adapter.navigate_to_object(
                SemanticNavigationGoal(target_object="沙发")
            )


class TestHabitatAdapterObjectMapping:
    """Verify Chinese→semantic object name mapping."""

    def test_known_objects_mapped(self):
        """All MVP seed objects have semantic mappings."""
        from chronopersona.embodied.habitat_adapter import _OBJECT_SEMANTIC_MAP

        expected = {"沙发", "床", "桌子", "椅子", "冰箱", "茶几"}
        assert set(_OBJECT_SEMANTIC_MAP.keys()) == expected

    def test_semantic_values_are_english(self):
        """Semantic values are lowercase English identifiers."""
        from chronopersona.embodied.habitat_adapter import _OBJECT_SEMANTIC_MAP

        for cn, en in _OBJECT_SEMANTIC_MAP.items():
            assert en.islower()
            assert en.replace("_", "").isalpha()
