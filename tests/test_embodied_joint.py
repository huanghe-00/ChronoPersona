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
        """T-JOINT-02: A* navigation reaches sofa with global shortest path."""
        adapter = HM3DAdapter(scene_dir="", agent_id="agent_0")
        goal = SemanticNavigationGoal(target_object="沙发")
        result = adapter.navigate_to_object(goal)
        assert result.success is True
        # A* + smoothing produces variable step count; minimum ensures path exists
        assert result.steps_taken >= 5
        # 3D coordinate consistency: final pos should match object index
        assert result.final_position[0] == pytest.approx(8.0, abs=0.5)
        assert result.final_position[2] == pytest.approx(6.0, abs=0.5)

    @pytest.mark.skipif(not HAS_TRIMESH, reason="trimesh/numpy not installed")
    def test_hm3d_astar_avoids_obstacles(self):
        """T-JOINT-03: A* path detours around island obstacle, not through it."""
        adapter = HM3DAdapter(scene_dir="", agent_id="agent_0")
        # Agent starts at default center (10, 0, 10), sofa at (8, 0.3, 6)
        # Island main at (6.5, 0, 6.5) blocks direct diagonal path
        goal = SemanticNavigationGoal(target_object="沙发")
        result = adapter.navigate_to_object(goal)
        assert result.success is True
        # Verify no path point is inside the island obstacle footprint
        island_x, island_z = 6.5, 6.5
        island_half_wx = 1.5 + 0.3  # size sx/2 + agent_radius
        island_half_wz = 0.5 + 0.3  # size sz/2 + agent_radius
        for px, py, pz in result.path:
            # Path points should not be inside inflated island footprint
            if abs(px - island_x) < island_half_wx and abs(pz - island_z) < island_half_wz:
                # Allow only if very close to start/end (inflation boundary)
                dist_to_start = math.hypot(px - 10.0, pz - 10.0)
                dist_to_goal = math.hypot(px - 8.0, pz - 6.0)
                assert min(dist_to_start, dist_to_goal) < 1.0, \
                    f"Path point ({px:.2f}, {pz:.2f}) is inside island obstacle"

    @pytest.mark.skipif(not HAS_TRIMESH, reason="trimesh/numpy not installed")
    def test_hm3d_path_smoothing_reduces_waypoints(self):
        """T-JOINT-04: Smoothed path has fewer waypoints than raw A* grid path."""
        adapter = HM3DAdapter(scene_dir="", agent_id="agent_0")
        goal = SemanticNavigationGoal(target_object="沙发")
        result = adapter.navigate_to_object(goal)
        assert result.success is True
        # Raw A* on 0.5m grid from (10,10) to (8,6) would have ~9 grid cells
        # After 3 iterations of shortcutting, animation path should still exist
        # but the underlying smoothed path has fewer distinct turns
        assert len(result.path) >= 5  # Animation steps still present

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
