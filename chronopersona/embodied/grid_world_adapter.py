"""GridWorldAdapter: 2D grid world embodied adapter."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractEmbodiedAdapter
from chronopersona.contracts.schemas import (
    EmbodiedState,
    LowLevelCommand,
    PerceptionResult,
    SpatialRecord,
)


class GridWorldAdapter(AbstractEmbodiedAdapter):
    """2D grid world adapter with coordinate, FOV, and movement support.

    Implements the AbstractEmbodiedAdapter interface for a simple
    grid-based environment. Agents have (x, y) coordinates and an
    orientation theta (radians). The field of view is computed as a
    cone of given angle and range.
    """

    def __init__(
        self,
        grid_width: int = 100,
        grid_height: int = 100,
        fov_angle_deg: float = 90.0,
        fov_range: float = 10.0,
    ) -> None:
        self._grid_width = grid_width
        self._grid_height = grid_height
        self._fov_angle_rad = math.radians(fov_angle_deg)
        self._fov_range = fov_range
        # agent_id -> (x, y, theta)
        self._agents: Dict[str, tuple[float, float, float]] = {}
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
        return LowLevelCommand(
            robot_type=robot_type,
            command=f"mock_{action_token}",
            params=params,
        )

    def add_object(self, agent_id: str, object_id: str, x: float, y: float) -> None:
        """Add an object to the agent's spatial memory."""
        self._ensure_agent(agent_id)
        record = SpatialRecord(object_id=object_id, x=x, y=y)
        self._spatial_memory[agent_id].append(record)
