#!/usr/bin/env python3
"""Joint embodied backend consistency tests."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

from chronopersona.embodied import HM3DAdapter, GridWorldAdapter
from chronopersona.contracts.schemas import SemanticNavigationGoal

# Check if trimesh is available for HM3D tests
HAS_TRIMESH = False
try:
    import trimesh  # noqa: F401
    import numpy  # noqa: F401
    HAS_TRIMESH = True
except ImportError:
    pass


class TestJointEmbodied:
    """Verify all backends expose identical EmbodiedState contracts."""

    @pytest.mark.skipif(not HAS_TRIMESH, reason="trimesh/numpy not installed")
    def test_hm3d_perception_fields(self):
        adapter = HM3DAdapter(scene_dir="", agent_id="agent_0")
        state = adapter.get_perception("agent_0")
        assert hasattr(state, "x")
        assert hasattr(state, "y")
        assert hasattr(state, "z")
        assert hasattr(state, "scene_id")
        assert state.scene_id == ""  # empty dir fallback

    @pytest.mark.skipif(not HAS_TRIMESH, reason="trimesh/numpy not installed")
    def test_hm3d_navigate_reaches_known_target(self):
        adapter = HM3DAdapter(scene_dir="", agent_id="agent_0")
        goal = SemanticNavigationGoal(target_object="沙发")
        result = adapter.navigate_to_object(goal)
        assert result.success is True
        assert result.steps_taken == 10
        # 3D coordinate consistency: final pos should match seed
        assert result.final_position[0] == pytest.approx(2.0, abs=0.1)
        assert result.final_position[2] == pytest.approx(3.0, abs=0.1)

    def test_grid_vs_hm3d_interface_parity(self):
        g = GridWorldAdapter()
        g_cmd = g.translate_action_token("approach_gently", {"speed": 0.5}, "grid_2d")
        assert g_cmd.command == "move_forward"
        if HAS_TRIMESH:
            h = HM3DAdapter(scene_dir="", agent_id="agent_0")
            h_cmd = h.translate_action_token("approach_gently", {"speed": 0.5}, "grid_2d")
            assert h_cmd.command == "move_forward"

    def test_backend_fallback_chain(self):
        """When habitat_sim is absent, HM3D should be constructible (if trimesh available)."""
        try:
            import habitat_sim  # noqa: F401
            pytest.skip("habitat_sim is installed, skip fallback test")
        except ImportError:
            pass
        if not HAS_TRIMESH:
            pytest.skip("trimesh/numpy not installed, HM3D unavailable")
        h = HM3DAdapter(scene_dir="", agent_id="a")
        assert h is not None
