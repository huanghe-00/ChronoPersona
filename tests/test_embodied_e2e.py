"""End-to-end embodied integration tests for P0/P1 closure."""

import math

import pytest

from chronopersona.agent_core.action_planner import ActionPlanner
from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import EmotionLabel, EmotionState
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestEmbodiedE2E:
    """E2E tests covering the full loop: LLM -> ActionPlanner -> execute -> coordinate update."""

    def _make_agent(self, x: float = 3.0, y: float = 4.0, theta: float = 0.0):
        adapter = GridWorldAdapter()
        adapter._agents["default"] = (x, y, theta)
        # Navigation targets (demonstrate detour capability)
        adapter.add_object("default", "沙发", 8.0, 6.0)
        adapter.add_object("default", "桌子", 5.0, 10.0)
        # Obstacle blocking direct path from (3,4) to sofa(8,6)
        adapter.add_object("default", "岛台", 6.5, 6.5)
        return StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
            action_planner=ActionPlanner(),
        ), adapter

    def test_approach_gently_moves_agent(self):
        """T-E2E-01: Standard branch approach_gently executes coordinate change."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        out = agent.run_turn("你能慢慢靠近吗", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.action_token == "approach_gently"
        state = adapter.get_perception("default")
        assert state.x > 3.0
        assert state.y == 4.0

    def test_retreat_slowly_moves_agent_backward(self):
        """T-E2E-02: Retreat moves agent opposite to facing direction."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        out = agent.run_turn("后退一下", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.action_token == "retreat_slowly"
        state = adapter.get_perception("default")
        assert state.x < 3.0
        assert state.y == 4.0

    def test_turn_to_user_changes_theta(self):
        """T-E2E-03: Turn action updates theta."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        out = agent.run_turn("转过去面对我", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.action_token == "turn_to_user"
        state = adapter.get_perception("default")
        assert state.theta != 0.0

    def test_look_around_rotates_90_degrees(self):
        """T-E2E-04: Look around rotates by 90 degrees."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        out = agent.run_turn("看看周围", branch_id="main")
        assert out.action_plan is not None
        assert out.action_plan.action_token == "look_around"
        state = adapter.get_perception("default")
        assert abs(state.theta - math.pi / 2) < 0.01

    def test_navigation_bypass_reaches_target(self):
        """T-E2E-05: Navigation bypass reaches sofa behind island obstacle."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        out = agent.run_turn("去沙发旁边", branch_id="main")
        assert "已到达" in out.reply_text or "无法找到" in out.reply_text
        state = adapter.get_perception("default")
        assert state.x == 8.0
        assert state.y == 6.0

    def test_emotion_modulation_reduces_speed(self):
        """T-E2E-06: CONCERNED emotion reduces approach speed to 0.25."""
        agent, adapter = self._make_agent(3.0, 4.0, 0.0)
        agent._emotion_state = EmotionState(
            current_state=EmotionLabel.CONCERNED,
            intensity=0.7,
            trigger_reason="User expressed negative emotion",
            confidence=0.9,
            valence=-0.7,
            arousal=0.6,
        )
        out = agent.run_turn("你能慢慢靠近吗", branch_id="main")
        state = adapter.get_perception("default")
        # CONCERNED speed_mult=0.5 * approach_gently speed=0.5 = 0.25 total displacement
        assert state.x == 3.25

    def test_fov_contains_nearby_object(self):
        """T-E2E-07: FOV computation includes object when facing correct direction."""
        adapter = GridWorldAdapter()
        # Agent at (8,5), facing north (theta=pi/2), sofa at (8,6) is directly ahead
        adapter._agents["default"] = (8.0, 5.0, math.pi / 2)
        adapter.add_object("default", "沙发", 8.0, 6.0)
        state = adapter.get_perception("default")
        assert "沙发" in state.fov_objects

    def test_fov_excludes_out_of_angle_object(self):
        """T-E2E-08: FOV excludes object outside cone angle."""
        adapter = GridWorldAdapter()
        # Agent at (8,5), facing east (theta=0), sofa at (8,6) is north (outside FOV)
        adapter._agents["default"] = (8.0, 5.0, 0.0)
        adapter.add_object("default", "沙发", 8.0, 6.0)
        state = adapter.get_perception("default")
        assert "沙发" not in state.fov_objects
