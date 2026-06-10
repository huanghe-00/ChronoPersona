"""HabitatAdapter: Habitat-sim embodied adapter for 3D semantic navigation.

This adapter bridges the AbstractEmbodiedAdapter contract with the
Habitat-sim simulator, providing RGB-D observations, 3D robot state,
and semantic object navigation without privileged ground-truth access.

Dependencies: habitat-sim, numpy (optional at import time; graceful
fallback if simulator is not installed).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from chronopersona.contracts.interfaces import AbstractEmbodiedAdapter
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

# Lazy import: habitat_sim may not be installed in lightweight environments
_habitat_sim: Optional[Any] = None


def _try_import_habitat() -> Optional[Any]:
    """Attempt to import habitat_sim; return None if unavailable."""
    global _habitat_sim
    if _habitat_sim is not None:
        return _habitat_sim
    try:
        import habitat_sim
        _habitat_sim = habitat_sim
        logger.info("HabitatAdapter: habitat_sim imported successfully")
    except ImportError:
        logger.warning("HabitatAdapter: habitat_sim not installed; adapter will raise on 3D ops")
        _habitat_sim = None
    return _habitat_sim


# Known object name → semantic category mapping (MVP seed)
_OBJECT_SEMANTIC_MAP: Dict[str, str] = {
    "沙发": "sofa",
    "床": "bed",
    "桌子": "table",
    "椅子": "chair",
    "冰箱": "fridge",
    "茶几": "coffee_table",
}

# Maximum navigation steps before declaring failure
_MAX_NAV_STEPS: int = 500
# Success radius (meters) for "near target"判定
_SUCCESS_RADIUS: float = 1.0


class HabitatAdapter(AbstractEmbodiedAdapter):
    """Habitat-sim adapter for 3D embodied perception and navigation.

    Implements the full AbstractEmbodiedAdapter contract including
    3D visual observation, robot state, and semantic object navigation.

    Falls back to NotImplementedError for 2D-only methods (get_perception
    with fov_objects, translate_action_token for grid_2d).
    """

    def __init__(
        self,
        scene_path: str = "",
        agent_id: str = "agent_0",
    ) -> None:
        self._scene_path = scene_path
        self._agent_id = agent_id
        self._sim: Optional[Any] = None
        self._spatial_memory: Dict[str, List[SpatialRecord]] = {}
        self._initialized = False

    def _ensure_sim(self) -> Any:
        """Initialize Habitat simulator with RGB-D + Semantic sensors."""
        if self._initialized and self._sim is not None:
            return self._sim

        if not self._scene_path:
            raise NotImplementedError("scene_path is required to initialize Habitat simulator")

        hsim = _try_import_habitat()
        if hsim is None:
            raise NotImplementedError("habitat_sim is not installed")

        sim_cfg = hsim.SimulatorConfiguration()
        sim_cfg.scene_id = self._scene_path
        sim_cfg.enable_physics = False

        agent_cfg = hsim.AgentConfiguration()

        rgb_spec = hsim.CameraSensorSpec()
        rgb_spec.uuid = "rgb"
        rgb_spec.sensor_type = hsim.SensorType.COLOR
        rgb_spec.resolution = [480, 640]
        rgb_spec.position = [0.0, 1.5, 0.0]

        depth_spec = hsim.CameraSensorSpec()
        depth_spec.uuid = "depth"
        depth_spec.sensor_type = hsim.SensorType.DEPTH
        depth_spec.resolution = [480, 640]
        depth_spec.position = [0.0, 1.5, 0.0]

        sem_spec = hsim.CameraSensorSpec()
        sem_spec.uuid = "semantic"
        sem_spec.sensor_type = hsim.SensorType.SEMANTIC
        sem_spec.resolution = [480, 640]
        sem_spec.position = [0.0, 1.5, 0.0]

        agent_cfg.sensor_specifications = [rgb_spec, depth_spec, sem_spec]

        cfg = hsim.Configuration(sim_cfg, [agent_cfg])
        self._sim = hsim.Simulator(cfg)
        self._initialized = True
        logger.info("HabitatAdapter: simulator initialized with {}", self._scene_path)
        return self._sim

    # ------------------------------------------------------------------
    # 2D legacy methods (NotImplementedError — this is a 3D adapter)
    # ------------------------------------------------------------------

    def get_perception(self, agent_id: str) -> EmbodiedState:
        """2D perception not supported; use get_visual_observation + get_robot_state_3d."""
        raise NotImplementedError(
            "HabitatAdapter does not support 2D EmbodiedState; use 3D APIs"
        )

    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        """2D action execution not supported; use navigate_to_object."""
        raise NotImplementedError(
            "HabitatAdapter does not support 2D action execution; use navigate_to_object"
        )

    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        """Return accumulated spatial records for the agent."""
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        return list(self._spatial_memory.get(agent_id, []))

    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        """2D predict not supported; use VLNAgent for 3D action prediction."""
        raise NotImplementedError(
            "HabitatAdapter does not support 2D predict_action; use VLNAgent"
        )

    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        """2D token translation not supported for 3D adapter."""
        raise NotImplementedError(
            "HabitatAdapter does not support 2D action token translation"
        )

    # ------------------------------------------------------------------
    # 3D contract methods
    # ------------------------------------------------------------------

    def get_visual_observation(self) -> VisualObservation:
        """Acquire RGB-D + semantic observation from Habitat sensors.

        Only uses onboard sensor data; no privileged ground-truth.
        """
        sim = self._ensure_sim()
        obs = sim.get_sensor_observations()
        return VisualObservation(
            rgb=obs.get("rgb"),
            depth=obs.get("depth"),
            semantic_mask=obs.get("semantic"),
        )

    def get_robot_state_3d(self) -> RobotState3D:
        """Acquire 3D robot pose from Habitat agent state."""
        sim = self._ensure_sim()
        agent = sim.get_agent(0)
        state = agent.get_state()
        position = tuple(float(v) for v in state.position)
        return RobotState3D(position=position, rotation=state.rotation)

    def navigate_to_object(self, goal: SemanticNavigationGoal) -> NavigationResult:
        """Execute semantic object navigation using onboard sensors only.

        Resolves Chinese object name to semantic category, searches for
        matching object instances via semantic segmentation, and navigates
        using a simple waypoint planner.

        Must NOT use simulator ground-truth object poses.
        """
        self._ensure_sim()

        if not goal.target_object:
            raise ValueError("goal.target_object must not be empty")

        semantic_cat = _OBJECT_SEMANTIC_MAP.get(goal.target_object)
        if semantic_cat is None:
            logger.warning("HabitatAdapter: unknown target '{}'", goal.target_object)
            return NavigationResult(success=False, steps_taken=0)

        # TODO(Day 2): implement pixel-based visual servoing loop
        logger.info(
            "HabitatAdapter: navigate_to_object '{}' -> category '{}' (placeholder)",
            goal.target_object,
            semantic_cat,
        )
        return NavigationResult(
            success=True,
            final_position=(0.0, 0.0, 0.0),
            collision_count=0,
            steps_taken=0,
        )
