"""HM3DAdapter: Lightweight 3D embodied adapter using trimesh (no habitat-sim).

Loads HM3D .basis.glb scenes, provides 3D navigation and semantic perception.
"""

from __future__ import annotations

import math
from pathlib import Path
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

HAS_TRIMESH = False
try:
    import trimesh
    import numpy as np
    HAS_TRIMESH = True
except ImportError:
    pass


# Pre-seeded object coordinates (aligned with frontend TARGETS and VLNAgent)
_DEFAULT_OBJECT_INDEX: Dict[str, List[Tuple[float, float, float]]] = {
    "沙发": [(2.0, 0.0, 3.0)],
    "床": [(8.0, 0.0, 12.0)],
    "桌子": [(3.0, 0.0, 2.0)],
    "椅子": [(5.0, 0.0, 5.0)],
    "冰箱": [(10.0, 0.0, 5.0)],
    "茶几": [(4.0, 0.0, 3.0)],
}


class HM3DAdapter(AbstractEmbodiedAdapter):
    """3D adapter for HM3D scenes using trimesh.

    Does not require habitat-sim. Falls back to bounding-box clamping
    when navmesh is unavailable.
    """

    def __init__(
        self,
        scene_dir: str = "",
        agent_id: str = "agent_0",
    ) -> None:
        if not HAS_TRIMESH:
            raise NotImplementedError(
                "HM3DAdapter requires trimesh and numpy. "
                "Install: pip install trimesh numpy"
            )
        self._scene_dir = Path(scene_dir) if scene_dir else None
        self._agent_id = agent_id
        self._mesh: Optional[Any] = None
        self._bounds: Optional[Any] = None
        self._object_index: Dict[str, List[Tuple[float, float, float]]] = dict(
            _DEFAULT_OBJECT_INDEX
        )
        self._agents: Dict[str, Tuple[float, float, float, float]] = {}  # x,y,z,theta
        self._spatial_memory: Dict[str, List[SpatialRecord]] = {}

        if self._scene_dir and self._scene_dir.exists():
            self._load_scene(self._scene_dir)

    def _load_scene(self, scene_dir: Path) -> None:
        glb_files = list(scene_dir.glob("*.basis.glb")) + list(
            scene_dir.glob("*.semantic.glb")
        )
        if not glb_files:
            logger.warning("No .glb found in {}, using fallback bounds", scene_dir)
            self._bounds = [[0.0, 0.0, 0.0], [20.0, 5.0, 20.0]]
            return

        self._mesh = trimesh.load(glb_files[0], force="mesh")
        self._bounds = self._mesh.bounds  # [[minx, miny, minz], [maxx, maxy, maxz]]
        logger.info("HM3DAdapter loaded {} with bounds {}", glb_files[0], self._bounds)

    def _ensure_agent(self, agent_id: str) -> None:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if agent_id not in self._agents:
            cx = (self._bounds[0][0] + self._bounds[1][0]) / 2 if self._bounds else 10.0
            cy = self._bounds[0][1] if self._bounds else 0.0
            cz = (self._bounds[0][2] + self._bounds[1][2]) / 2 if self._bounds else 10.0
            self._agents[agent_id] = (cx, cy, cz, 0.0)
            self._spatial_memory[agent_id] = []

    def get_perception(self, agent_id: str) -> EmbodiedState:
        self._ensure_agent(agent_id)
        x, y, z, theta = self._agents[agent_id]
        fov = self._compute_fov(x, y, z, theta)
        scene_name = ""
        if self._scene_dir:
            scene_name = self._scene_dir.name
        return EmbodiedState(
            agent_id=agent_id,
            x=x,
            y=y,
            z=z,
            theta=theta,
            scene_id=scene_name,
            fov_objects=fov,
        )

    def _compute_fov(
        self, x: float, y: float, z: float, theta: float
    ) -> List[str]:
        """Simplified 3D frustum: horizontal distance + angle check."""
        objects: List[str] = []
        for label, positions in self._object_index.items():
            for (ox, oy, oz) in positions:
                dx = ox - x
                dz = oz - z
                dist = math.hypot(dx, dz)
                if dist > 10.0:
                    continue
                angle_to = math.atan2(dz, dx)
                angle_diff = abs((angle_to - theta + math.pi) % (2 * math.pi) - math.pi)
                if angle_diff <= math.radians(45.0):
                    objects.append(label)
                    break
        return objects

    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        self._ensure_agent(agent_id)
        x, y, z, theta = self._agents[agent_id]
        if isinstance(action, dict):
            dx = float(action.get("dx", 0.0))
            dy = float(action.get("dy", 0.0))
            dz = float(action.get("dz", 0.0))
            dtheta = float(action.get("dtheta", 0.0))
        else:
            dx, dy, dz, dtheta = 0.0, 0.0, 0.0, 0.0

        new_x = x + dx
        new_y = y + dy
        new_z = z + dz
        new_theta = (theta + dtheta) % (2 * math.pi)

        if self._bounds is not None:
            new_x = max(self._bounds[0][0], min(self._bounds[1][0], new_x))
            new_y = max(self._bounds[0][1], min(self._bounds[1][1], new_y))
            new_z = max(self._bounds[0][2], min(self._bounds[1][2], new_z))

        self._agents[agent_id] = (new_x, new_y, new_z, new_theta)
        return PerceptionResult(success=True)

    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        self._ensure_agent(agent_id)
        return list(self._spatial_memory.get(agent_id, []))

    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        if not task_desc:
            raise ValueError("task_desc must not be empty")
        for obj in percept.fov_objects:
            if obj in task_desc:
                return {"action_token": "approach", "target": obj}
        return {"action_token": "idle"}

    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        if not action_token or not robot_type:
            raise ValueError("action_token and robot_type must not be empty")

        # Unified mapping for both hm3d and grid_2d
        if action_token == "approach" or action_token == "approach_gently":
            return LowLevelCommand(
                robot_type=robot_type,
                command="move_forward",
                params={
                    "distance": params.get("distance", 1.0),
                    "speed": params.get("speed", 0.5) * params.get("speed_mult", 1.0),
                },
            )
        if action_token == "retreat_slowly":
            return LowLevelCommand(
                robot_type=robot_type,
                command="move_backward",
                params={
                    "distance": params.get("distance", 1.0),
                    "speed": params.get("speed", 0.5) * params.get("speed_mult", 1.0),
                },
            )
        if action_token == "turn_to_user":
            return LowLevelCommand(
                robot_type=robot_type,
                command="turn_toward",
                params={
                    "target_x": params.get("target_x", 0.0),
                    "target_y": params.get("target_y", 0.0),
                    "target_z": params.get("target_z", 0.0),
                },
            )
        if action_token == "interact":
            return LowLevelCommand(
                robot_type=robot_type,
                command="interact_with",
                params={"object_id": params.get("object_id", "")},
            )
        if action_token == "look_around":
            return LowLevelCommand(
                robot_type=robot_type,
                command="scan_fov",
                params={"range": params.get("range", 5.0)},
            )
        return LowLevelCommand(
            robot_type=robot_type,
            command=f"mock_{action_token}",
            params=params,
        )

    def get_visual_observation(self) -> VisualObservation:
        raise NotImplementedError(
            "HM3DAdapter does not support visual observation in MVA"
        )

    def get_robot_state_3d(self) -> RobotState3D:
        self._ensure_agent(self._agent_id)
        x, y, z, theta = self._agents[self._agent_id]
        return RobotState3D(
            position=(x, y, z),
            rotation=(0.0, math.sin(theta / 2), 0.0, math.cos(theta / 2)),
        )

    def navigate_to_object(self, goal: SemanticNavigationGoal) -> NavigationResult:
        if not goal.target_object:
            raise ValueError("goal.target_object must not be empty")

        target = goal.target_object.strip()
        positions = self._object_index.get(target, [])
        if not positions:
            # Try fuzzy match
            for k, v in self._object_index.items():
                if target in k or k in target:
                    positions = v
                    target = k
                    break

        if not positions:
            x, y, z, _ = self._agents.get(self._agent_id, (0.0, 0.0, 0.0, 0.0))
            return NavigationResult(
                success=False, final_position=(x, y, z), steps_taken=0, path=[]
            )

        tx, ty, tz = positions[0]
        x, y, z, theta = self._agents.get(self._agent_id, (0.0, 0.0, 0.0, 0.0))

        # Linear interpolation over 10 steps
        path: List[Tuple[float, float, float]] = []
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            px = x + (tx - x) * t
            py = y + (ty - y) * t
            pz = z + (tz - z) * t
            path.append((px, py, pz))

        # Update agent state to final position
        final_theta = math.atan2(tz - z, tx - x)
        self._agents[self._agent_id] = (tx, ty, tz, final_theta)
        return NavigationResult(
            success=True,
            final_position=(tx, ty, tz),
            steps_taken=steps,
            collision_count=0,
            path=path,
        )
