"""GridWorldAdapter: 2D grid world embodied adapter."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

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

DEFAULT_GRID_WIDTH: int = 100
DEFAULT_GRID_HEIGHT: int = 100
DEFAULT_FOV_ANGLE_DEG: float = 90.0
DEFAULT_FOV_RANGE: float = 10.0


class GridWorldAdapter(AbstractEmbodiedAdapter):
    """2D grid world adapter with coordinate, FOV, and movement support.

    Implements the AbstractEmbodiedAdapter interface for a simple
    grid-based environment. Agents have (x, y) coordinates and an
    orientation theta (radians). The field of view is computed as a
    cone of given angle and range.
    """

    def __init__(
        self,
        grid_width: int = DEFAULT_GRID_WIDTH,
        grid_height: int = DEFAULT_GRID_HEIGHT,
        fov_angle_deg: float = DEFAULT_FOV_ANGLE_DEG,
        fov_range: float = DEFAULT_FOV_RANGE,
    ) -> None:
        self._grid_width = grid_width
        self._grid_height = grid_height
        self._fov_angle_rad = math.radians(fov_angle_deg)
        self._fov_range = fov_range
        # agent_id -> (x, y, theta)
        self._agents: Dict[str, Tuple[float, float, float]] = {}
        # agent_id -> list of SpatialRecord
        self._spatial_memory: Dict[str, List[SpatialRecord]] = {}

    def _ensure_agent(self, agent_id: str) -> None:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if agent_id not in self._agents:
            self._agents[agent_id] = (0.0, 0.0, 0.0)
            self._spatial_memory[agent_id] = []

    def get_perception(self, agent_id: str) -> EmbodiedState:
        """Return current embodied state including FOV objects."""
        self._ensure_agent(agent_id)
        x, y, theta = self._agents[agent_id]
        fov_objects = self._compute_fov(agent_id, x, y, theta)
        return EmbodiedState(
            agent_id=agent_id,
            x=x,
            y=y,
            theta=theta,
            fov_objects=fov_objects,
        )

    def _compute_fov(
        self, agent_id: str, x: float, y: float, theta: float
    ) -> List[str]:
        """Compute objects in field of view based on spatial memory."""
        objects: List[str] = []
        for record in self._spatial_memory.get(agent_id, []):
            dx = record.x - x
            dy = record.y - y
            dist = math.hypot(dx, dy)
            if dist > self._fov_range:
                continue
            angle_to = math.atan2(dy, dx)
            angle_diff = abs((angle_to - theta + math.pi) % (2 * math.pi) - math.pi)
            if angle_diff <= self._fov_angle_rad / 2:
                objects.append(record.object_id)
        return objects

    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        """Execute a movement action and return perception result."""
        self._ensure_agent(agent_id)
        x, y, theta = self._agents[agent_id]
        if isinstance(action, dict):
            dx = float(action.get("dx", 0.0))
            dy = float(action.get("dy", 0.0))
            dtheta = float(action.get("dtheta", 0.0))
        else:
            dx, dy, dtheta = 0.0, 0.0, 0.0
        new_x = max(0.0, min(self._grid_width - 1, x + dx))
        new_y = max(0.0, min(self._grid_height - 1, y + dy))
        new_theta = (theta + dtheta) % (2 * math.pi)
        self._agents[agent_id] = (new_x, new_y, new_theta)
        return PerceptionResult(success=True)

    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        """Return spatial records for the agent."""
        self._ensure_agent(agent_id)
        return list(self._spatial_memory.get(agent_id, []))

    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        """Predict a simple action based on task description."""
        if not task_desc:
            raise ValueError("task_desc must not be empty")
        # Simple heuristic: move towards a target if mentioned
        target = None
        for obj in percept.fov_objects:
            if obj in task_desc:
                target = obj
                break
        if target:
            return {"action_token": "approach", "target": target}
        return {"action_token": "idle"}

    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        """Translate high-level action token to low-level command."""
        if not action_token or not robot_type:
            raise ValueError("action_token and robot_type must not be empty")
        if action_token == "approach":
            return LowLevelCommand(
                robot_type=robot_type,
                command="move_toward",
                params={"target": params.get("target", ""), "speed": 1.0},
            )
        if action_token == "approach_gently":
            return self._handle_approach_gently(action_token, params, robot_type)
        if action_token == "retreat_slowly":
            return self._handle_retreat_slowly(action_token, params, robot_type)
        if action_token == "turn_to_user":
            return self._handle_turn_to_user(action_token, params, robot_type)
        if action_token == "interact":
            return self._handle_interact(action_token, params, robot_type)
        if action_token == "look_around":
            return self._handle_look_around(action_token, params, robot_type)
        return LowLevelCommand(
            robot_type=robot_type,
            command=f"mock_{action_token}",
            params=params,
        )

    def _handle_approach_gently(
        self, action_token: str, params: Dict[str, Any], robot_type: str
    ) -> LowLevelCommand:
        if robot_type == "grid_2d":
            speed = params.get("speed", 1.0) * params.get("speed_mult", 1.0)
            return LowLevelCommand(
                robot_type="grid_2d",
                command="move_forward",
                params={"distance": params.get("distance", 1.0), "speed": speed},
            )
        if robot_type == "ros2_mobile":
            linear = params.get("speed", 0.5) * params.get("speed_mult", 1.0)
            return LowLevelCommand(
                robot_type="ros2_mobile",
                command="cmd_vel",
                params={"linear": linear, "angular": 0.0},
            )
        raise ValueError(f"Unsupported robot_type: {robot_type}")

    def _handle_retreat_slowly(
        self, action_token: str, params: Dict[str, Any], robot_type: str
    ) -> LowLevelCommand:
        if robot_type == "grid_2d":
            speed = params.get("speed", 0.5) * params.get("speed_mult", 1.0)
            return LowLevelCommand(
                robot_type="grid_2d",
                command="move_backward",
                params={"distance": params.get("distance", 1.0), "speed": speed},
            )
        if robot_type == "ros2_mobile":
            linear = -(params.get("speed", 0.5) * params.get("speed_mult", 1.0))
            return LowLevelCommand(
                robot_type="ros2_mobile",
                command="cmd_vel",
                params={"linear": linear, "angular": 0.0},
            )
        raise ValueError(f"Unsupported robot_type: {robot_type}")

    def _handle_turn_to_user(
        self, action_token: str, params: Dict[str, Any], robot_type: str
    ) -> LowLevelCommand:
        if robot_type == "grid_2d":
            return LowLevelCommand(
                robot_type="grid_2d",
                command="turn_toward",
                params={
                    "target_x": params.get("target_x", 0.0),
                    "target_y": params.get("target_y", 0.0),
                },
            )
        if robot_type == "ros2_mobile":
            return LowLevelCommand(
                robot_type="ros2_mobile",
                command="navigate_to",
                params={
                    "target_x": params.get("target_x", 0.0),
                    "target_y": params.get("target_y", 0.0),
                },
            )
        raise ValueError(f"Unsupported robot_type: {robot_type}")

    def _handle_interact(
        self, action_token: str, params: Dict[str, Any], robot_type: str
    ) -> LowLevelCommand:
        if robot_type == "grid_2d":
            return LowLevelCommand(
                robot_type="grid_2d",
                command="interact_with",
                params={"object_id": params.get("object_id", "")},
            )
        if robot_type == "ros2_mobile":
            return LowLevelCommand(
                robot_type="ros2_mobile",
                command="interact_with",
                params={"object_id": params.get("object_id", "")},
            )
        raise ValueError(f"Unsupported robot_type: {robot_type}")

    def _handle_look_around(
        self, action_token: str, params: Dict[str, Any], robot_type: str
    ) -> LowLevelCommand:
        if robot_type == "grid_2d":
            return LowLevelCommand(
                robot_type="grid_2d",
                command="scan_fov",
                params={"range": params.get("range", 5.0)},
            )
        if robot_type == "ros2_mobile":
            return LowLevelCommand(
                robot_type="ros2_mobile",
                command="scan_fov",
                params={"range": params.get("range", 5.0)},
            )
        raise ValueError(f"Unsupported robot_type: {robot_type}")

    def get_visual_observation(self) -> VisualObservation:
        """Not supported in 2D grid world."""
        raise NotImplementedError(
            "GridWorldAdapter does not support 3D visual observation"
        )

    def get_robot_state_3d(self) -> RobotState3D:
        """Not supported in 2D grid world."""
        raise NotImplementedError(
            "GridWorldAdapter does not support 3D robot state"
        )

    def navigate_to_object(self, goal: SemanticNavigationGoal) -> NavigationResult:
        """Semantic navigation in 2D grid using world model (no privileged simulator access)."""
        if not goal.target_object:
            raise ValueError("goal.target_object must not be empty")

        # Default agent for MVP single-agent demo
        agent_id = "default"
        self._ensure_agent(agent_id)

        name = goal.target_object.strip().lower()

        # Priority 1: dynamic objects in spatial memory (embodied perception)
        for record in self._spatial_memory.get(agent_id, []):
            rid = record.object_id.strip().lower()
            if rid == name or name in rid or rid in name:
                x, y = record.x, record.y
                _, _, theta = self._agents[agent_id]
                self._agents[agent_id] = (float(x), float(y), theta)
                return NavigationResult(
                    success=True,
                    final_position=(float(x), float(y), 0.0),
                )

        # Priority 2: hard-coded semantic map (MVA fallback)
        target_map = {
            "沙发": (2.0, 3.0), "sofa": (2.0, 3.0),
            "床": (8.0, 12.0), "bed": (8.0, 12.0),
            "桌子": (3.0, 2.0), "table": (3.0, 2.0),
            "厨房": (15.0, 5.0), "kitchen": (15.0, 5.0),
        }

        pos = target_map.get(name)
        if pos is None:
            # Fuzzy match: check if any key is substring of input or vice versa
            for key, value in target_map.items():
                if key in name or name in key:
                    pos = value
                    break

        if pos is None:
            return NavigationResult(
                success=False,
                final_position=(*self._agents[agent_id][:2], 0.0),
            )

        x, y = pos
        _, _, theta = self._agents[agent_id]
        self._agents[agent_id] = (float(x), float(y), theta)
        return NavigationResult(
            success=True,
            final_position=(float(x), float(y), 0.0),
        )

    def add_object(self, agent_id: str, object_id: str, x: float, y: float) -> None:
        """Add an object to the agent's spatial memory."""
        self._ensure_agent(agent_id)
        record = SpatialRecord(object_id=object_id, x=x, y=y)
        self._spatial_memory[agent_id].append(record)
