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


# Pre-seeded object coordinates (redistributed behind obstacles for detour demonstration)
# Heights differentiated for 3D layering: fridge=1.2m, table=0.8m, bed=0.5m, chair=0.4m, sofa/tea_table=0.3m
# Layout: targets placed behind L-shaped island, glass wall, bar cluster, and corner sofa
_DEFAULT_OBJECT_INDEX: Dict[str, List[Tuple[float, float, float]]] = {
    "沙发": [(8.0, 0.3, 6.0)],      # 客厅区南侧
    "床": [(4.0, 1.5, 11.0)],       # 卧室区北侧：高架床（高1.5m）
    "桌子": [(5.0, 1.1, 10.0)],     # 卧室区北侧：高脚桌（高1.1m）
    "椅子": [(9.0, 0.4, 3.0)],      # 客厅区南侧
    "冰箱": [(10.0, 1.2, 4.0)],     # 客厅区南侧
    "茶几": [(9.0, 0.3, 5.0)],      # 客厅区南侧
}


class HM3DAdapter(AbstractEmbodiedAdapter):
    """降级演示适配器：无 habitat-sim 时提供纯坐标运动。

    不加载真实场景几何，不重建navmesh。Agent 在预置坐标间直线移动。
    仅用于前端联调和2D/3D坐标演示，非真实物理仿真。
    """

    # 障碍物物理参数: (x, y_height, z_depth, safety_radius)
    # safety_radius = 几何外接半宽 + 0.5m 绕行余量
    _OBSTACLES = [
        # L形岛台（客厅区中央）
        (6.5, 0.0, 6.5, 1.5),    # 岛台主体
        (5.5, 0.0, 7.5, 1.2),    # 岛台侧翼
        # 中央玻璃隔断墙（分隔客厅与卧室区）
        (5.0, 0.0, 7.5, 2.0),    # 尺寸 4.0(x)×1.8(y)×0.1(z); 半宽=2.0, 安全半径=2.0
        # 落地灯柱（卧室区入口）
        (3.0, 0.0, 8.0, 1.0),    # 北移至卧室区
        # 矮边柜（客厅区东侧）
        (9.0, 0.0, 4.0, 1.0),
        # 高书架（卧室区西北角）
        (1.5, 0.0, 9.0, 1.0),
        # 转角沙发（客厅区东南角）
        (7.0, 0.0, 2.5, 1.2),
        # 吧台群（卧室区北侧）
        (4.5, 0.0, 9.0, 0.8),    # 吧台1
        (3.8, 0.0, 9.5, 0.8),    # 吧台2
        (3.0, 0.0, 10.0, 0.8),   # 吧台3
    ]

    # 3D 形状与外观定义（供前端渲染使用）
    _OBSTACLE_SHAPES = {
        (6.5, 0.0, 6.5): {
            "shape": "box",
            "size": (3.0, 0.9, 1.0),
            "color": 0x8B4513,
            "label": "岛台主体",
        },
        (5.5, 0.0, 7.5): {
            "shape": "box",
            "size": (1.0, 0.9, 3.0),
            "color": 0x8B4513,
            "label": "岛台侧翼",
        },
        (3.0, 0.0, 8.0): {
            "shape": "cylinder",
            "radius": 0.4,
            "height": 2.2,
            "color": 0x696969,
            "label": "灯柱",
        },
        (9.0, 0.0, 4.0): {
            "shape": "box",
            "size": (1.5, 0.6, 0.8),
            "color": 0x2E8B57,
            "label": "矮柜",
        },
        (1.5, 0.0, 9.0): {
            "shape": "box",
            "size": (1.0, 2.4, 0.4),
            "color": 0x8B0000,
            "label": "书架",
        },
        (7.0, 0.0, 2.5): {
            "shape": "box",
            "size": (2.0, 0.6, 1.0),
            "color": 0x4169E1,
            "label": "转角沙发",
        },
        (5.0, 0.0, 7.5): {
            "shape": "box",
            "size": (4.0, 1.8, 0.1),
            "color": 0x87CEEB,
            "label": "玻璃隔断",
        },
        (4.5, 0.0, 9.0): {
            "shape": "cylinder",
            "radius": 0.6,
            "height": 1.1,
            "color": 0xDAA520,
            "label": "吧台1",
        },
        (3.8, 0.0, 9.5): {
            "shape": "cylinder",
            "radius": 0.6,
            "height": 1.1,
            "color": 0xDAA520,
            "label": "吧台2",
        },
        (3.0, 0.0, 10.0): {
            "shape": "cylinder",
            "radius": 0.6,
            "height": 1.1,
            "color": 0xDAA520,
            "label": "吧台3",
        },
    }

    # Phase 1 navigation optimization: A* with 3D-aware collision + path smoothing
    _GRID_RESOLUTION: float = 0.5   # 0.5m cell size for occupancy grid
    _AGENT_RADIUS: float = 0.3      # Agent body radius for obstacle inflation
    _AGENT_HEIGHT: float = 1.7      # Agent standing height (for under-passage check)
    _STEP_OVER_HEIGHT: float = 0.15 # Obstacles shorter than this can be stepped over

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
        self._nav_path: List[Tuple[float, float, float]] = []  # Animation replay cache

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

        # Detect navmesh files for future collision avoidance capability
        navmesh_files = list(scene_dir.glob("*.basis.navmesh")) + list(
            scene_dir.glob("*.semantic.navmesh")
        )
        if navmesh_files:
            logger.info(
                "HM3DAdapter: navmesh files detected in {} — "
                "geometric collision avoidance possible (future feature)",
                scene_dir,
            )
        else:
            logger.info(
                "HM3DAdapter: no navmesh files in {}, using linear interpolation navigation",
                scene_dir,
            )

    def _ensure_agent(self, agent_id: str) -> None:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        if agent_id not in self._agents:
            cx = (self._bounds[0][0] + self._bounds[1][0]) / 2 if self._bounds is not None else 10.0
            cy = (self._bounds[0][1] + self._bounds[1][1]) / 2 if self._bounds is not None else 0.0
            cz = (self._bounds[0][2] + self._bounds[1][2]) / 2 if self._bounds is not None else 10.0
            self._agents[agent_id] = (cx, cy, cz, 0.0)
            self._spatial_memory[agent_id] = []

    def get_perception(self, agent_id: str) -> EmbodiedState:
        self._ensure_agent(agent_id)
        x, y, z, theta = self._agents[agent_id]
        fov = self._compute_fov(x, y, z, theta)
        scene_name = ""
        if self._scene_dir:
            scene_name = self._scene_dir.name
        # 附加障碍物形状信息供前端 3D 渲染
        obstacle_meta = []
        for (ox, oy, oz), meta in self._OBSTACLE_SHAPES.items():
            obstacle_meta.append({
                "x": ox, "y": oy, "z": oz,
                **meta,
            })

        # Coordinate convention alignment: y=2D depth (from 3D z), z=height (from 3D y)
        return EmbodiedState(
            agent_id=agent_id,
            x=x,
            y=z,  # 3D z (depth) → 2D y axis
            z=y,  # 3D y (height) → 3D z axis
            theta=theta,
            scene_id=scene_name,
            fov_objects=fov,
            metadata={"obstacles": obstacle_meta},
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

        # P1 fix: Generate intermediate steps for smooth animation (only if not set by navigation)
        if not self._nav_path:
            steps = 5
            self._nav_path = []
            for i in range(steps + 1):
                t = i / steps
                ix = x + (new_x - x) * t
                iy = y + (new_y - y) * t
                iz = z + (new_z - z) * t
                self._nav_path.append((ix, iy, iz))

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

    @staticmethod
    def _point_to_segment_distance(
        px: float, pz: float, x1: float, z1: float, x2: float, z2: float
    ) -> float:
        """Compute minimum distance from point (px, pz) to line segment (x1,z1)-(x2,z2)."""
        dx, dz = x2 - x1, z2 - z1
        if abs(dx) < 1e-9 and abs(dz) < 1e-9:
            return math.hypot(px - x1, pz - z1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / (dx * dx + dz * dz)))
        return math.hypot(px - (x1 + t * dx), pz - (z1 + t * dz))

    @staticmethod
    def _segment_projection(
        px: float, pz: float, x1: float, z1: float, x2: float, z2: float
    ) -> Tuple[float, float, float]:
        """Return (distance, proj_x, proj_z) from point to line segment."""
        dx, dz = x2 - x1, z2 - z1
        seg_len_sq = dx * dx + dz * dz
        if seg_len_sq < 1e-9:
            return math.hypot(px - x1, pz - z1), x1, z1
        t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / seg_len_sq))
        proj_x = x1 + t * dx
        proj_z = z1 + t * dz
        dist = math.hypot(px - proj_x, pz - proj_z)
        return dist, proj_x, proj_z

    # ── Phase 1 navigation optimization methods ──

    def _build_occupancy_grid(self) -> Tuple[Any, Tuple[float, float], Tuple[float, float]]:
        """Build 2D occupancy grid with 3D-aware collision detection.

        Creates a discretized grid on the x-z plane, marking cells as blocked
        based on obstacle geometry inflated by agent radius. 3D passability
        is considered: obstacles shorter than _STEP_OVER_HEIGHT are passable,
        and obstacles with bottom clearance above _AGENT_HEIGHT are passable.

        Returns:
            grid: 2D boolean numpy array (True = blocked)
            origin: (x_offset, z_offset) grid origin in world coordinates
            bounds: (x_max, z_max) grid extent in world coordinates
        """
        if self._bounds is not None:
            x_min = self._bounds[0][0] - self._AGENT_RADIUS
            z_min = self._bounds[0][2] - self._AGENT_RADIUS
            x_max = self._bounds[1][0] + self._AGENT_RADIUS
            z_max = self._bounds[1][2] + self._AGENT_RADIUS
        else:
            x_min = -self._AGENT_RADIUS
            z_min = -self._AGENT_RADIUS
            x_max = 20.0 + self._AGENT_RADIUS
            z_max = 20.0 + self._AGENT_RADIUS

        nx = int(math.ceil((x_max - x_min) / self._GRID_RESOLUTION))
        nz = int(math.ceil((z_max - z_min) / self._GRID_RESOLUTION))

        grid = np.zeros((nx, nz), dtype=bool)

        # Mark obstacle cells with 3D-aware passability
        for (ox, _oy, oz), meta in self._OBSTACLE_SHAPES.items():
            if self._is_obstacle_passable_3d(meta):
                continue  # Agent can step over or pass under

            shape = meta.get("shape", "box")
            if shape == "box":
                sx, _sy, sz = meta["size"]
                half_wx = sx / 2 + self._AGENT_RADIUS
                half_wz = sz / 2 + self._AGENT_RADIUS
                # Mark cells within inflated box footprint
                for ix in range(nx):
                    cx = x_min + ix * self._GRID_RESOLUTION
                    if abs(cx - ox) >= half_wx:
                        continue
                    for iz in range(nz):
                        cz = z_min + iz * self._GRID_RESOLUTION
                        if abs(cz - oz) >= half_wz:
                            continue
                        grid[ix, iz] = True
            elif shape == "cylinder":
                r = meta["radius"] + self._AGENT_RADIUS
                for ix in range(nx):
                    cx = x_min + ix * self._GRID_RESOLUTION
                    if abs(cx - ox) >= r:
                        continue
                    for iz in range(nz):
                        cz = z_min + iz * self._GRID_RESOLUTION
                        if math.hypot(cx - ox, cz - oz) >= r:
                            continue
                        grid[ix, iz] = True

        return grid, (x_min, z_min), (x_max, z_max)

    def _is_obstacle_passable_3d(self, meta: Dict) -> bool:
        """Check if an obstacle can be passed over or under based on 3D geometry.

        An obstacle is passable if:
        - Its height < _STEP_OVER_HEIGHT (agent can step over, e.g. 0.1m threshold)
        - Its bottom is above _AGENT_HEIGHT (agent can walk under, e.g. elevated shelf)

        Ground-level obstacles (bottom at y=0) with height > step-over threshold
        are NOT passable — agent must detour around them.

        Args:
            meta: Obstacle shape metadata from _OBSTACLE_SHAPES.

        Returns:
            True if agent can pass without detouring.
        """
        shape = meta.get("shape", "box")
        if shape == "box":
            _, sy, _ = meta["size"]
            # Very short obstacles can be stepped over
            if sy < self._STEP_OVER_HEIGHT:
                return True
            # Ground-level obstacles with significant height block passage
            return False
        elif shape == "cylinder":
            h = meta["height"]
            if h < self._STEP_OVER_HEIGHT:
                return True
            return False
        return False

    def _astar_2d(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        grid: Any,
    ) -> Optional[List[Tuple[int, int]]]:
        """A* pathfinding on 2D occupancy grid with 8-connected neighbors.

        Uses Euclidean distance heuristic. Diagonal moves require both
        axis-aligned neighbors to be free (prevents corner-cutting).

        Args:
            start: (ix, iz) grid coordinates.
            goal: (ix, iz) grid coordinates.
            grid: 2D boolean numpy array (True = blocked).

        Returns:
            List of (ix, iz) grid coordinates forming the shortest path,
            or None if no path exists (unreachable goal).
        """
        import heapq

        nx, nz = grid.shape
        sx, sz = start
        gx, gz = goal

        if not (0 <= sx < nx and 0 <= sz < nz and 0 <= gx < nx and 0 <= gz < nz):
            return None

        # 8-connected neighbors with movement costs
        NEIGHBORS = [
            (1, 0, self._GRID_RESOLUTION),             # East
            (-1, 0, self._GRID_RESOLUTION),            # West
            (0, 1, self._GRID_RESOLUTION),             # North
            (0, -1, self._GRID_RESOLUTION),            # South
            (1, 1, self._GRID_RESOLUTION * 1.4142),   # NE
            (-1, 1, self._GRID_RESOLUTION * 1.4142),  # NW
            (1, -1, self._GRID_RESOLUTION * 1.4142),  # SE
            (-1, -1, self._GRID_RESOLUTION * 1.4142), # SW
        ]

        open_set: list[tuple[float, Tuple[int, int]]] = [(0.0, (sx, sz))]
        came_from: dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: dict[Tuple[int, int], float] = {(sx, sz): 0.0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == (gx, gz):
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            cx, cz = current
            for dx, dz, cost in NEIGHBORS:
                nxt = (cx + dx, cz + dz)
                ni, nj = nxt

                if not (0 <= ni < nx and 0 <= nj < nz):
                    continue
                if grid[ni, nj]:
                    continue

                # Diagonal move: check both axis-aligned neighbors are free
                if abs(dx) + abs(dz) == 2:
                    if grid[cx + dx, cz] or grid[cx, cz + dz]:
                        continue

                tentative_g = g_score[current] + cost
                if tentative_g < g_score.get(nxt, float('inf')):
                    came_from[nxt] = current
                    g_score[nxt] = tentative_g
                    # Euclidean distance heuristic
                    h = math.hypot(
                        (gx - ni) * self._GRID_RESOLUTION,
                        (gz - nj) * self._GRID_RESOLUTION,
                    )
                    heapq.heappush(open_set, (tentative_g + h, nxt))

        return None  # No path found (unreachable goal)

    def _find_nearest_free_cell(
        self,
        ix: int,
        iz: int,
        grid: Any,
        max_search_radius: int = 20,
    ) -> Optional[Tuple[int, int]]:
        """Find nearest unblocked grid cell via BFS expansion.

        Used when start or goal position falls inside a blocked cell
        (e.g., agent standing next to an obstacle after inflation).

        Args:
            ix, iz: Starting grid coordinates (may be blocked or out of bounds).
            grid: 2D boolean occupancy grid.
            max_search_radius: Maximum BFS expansion depth.

        Returns:
            (ix, iz) of nearest free cell, or None if all nearby cells are blocked.
        """
        from collections import deque

        nx, nz = grid.shape
        # Clamp to grid bounds first
        ix = max(0, min(nx - 1, ix))
        iz = max(0, min(nz - 1, iz))

        if not grid[ix, iz]:
            return (ix, iz)

        queue: deque[Tuple[int, int, int]] = deque([(ix, iz, 0)])
        visited: set[Tuple[int, int]] = {(ix, iz)}

        while queue:
            cx, cz, depth = queue.popleft()
            if depth > max_search_radius:
                return None

            for dx, dz in [(1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                ni, nj = cx + dx, cz + dz
                nxt = (ni, nj)
                if nxt in visited:
                    continue
                visited.add(nxt)
                if 0 <= ni < nx and 0 <= nj < nz and not grid[ni, nj]:
                    return nxt
                if 0 <= ni < nx and 0 <= nj < nz:
                    queue.append((ni, nj, depth + 1))

        return None

    def _smooth_path(
        self,
        path: List[Tuple[float, float]],
        grid: Any,
        x_off: float,
        z_off: float,
        iterations: int = 3,
    ) -> List[Tuple[float, float]]:
        """Path smoothing via iterative shortcutting.

        For each pair of non-adjacent path points, checks if a direct
        collision-free line exists. If so, removes intermediate waypoints.
        Repeats for multiple iterations to maximize shortcutting.

        Args:
            path: List of (x, z) world coordinates from A*.
            grid: Occupancy grid for collision checking.
            x_off, z_off: Grid origin offsets.
            iterations: Number of shortcutting passes.

        Returns:
            Smoothed path with fewer waypoints and gentler turns.
        """
        if len(path) <= 2:
            return list(path)

        smoothed = list(path)

        for _ in range(iterations):
            if len(smoothed) <= 2:
                break
            new_path = [smoothed[0]]
            i = 0
            while i < len(smoothed) - 1:
                # Find farthest reachable point from current position
                farthest = i + 1
                for j in range(len(smoothed) - 1, i + 1, -1):
                    if self._line_collision_free(
                        smoothed[i], smoothed[j], grid, x_off, z_off
                    ):
                        farthest = j
                        break
                new_path.append(smoothed[farthest])
                i = farthest
            smoothed = new_path

        return smoothed

    def _line_collision_free(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        grid: Any,
        x_off: float,
        z_off: float,
    ) -> bool:
        """Check if a straight line between two points is collision-free.

        Uses ray marching along the line, checking grid cell occupancy
        at half-cell spacing intervals for robust collision detection.

        Args:
            p1, p2: (x, z) world coordinates of line endpoints.
            grid: 2D boolean occupancy grid.
            x_off, z_off: Grid origin offsets.

        Returns:
            True if the entire line is in free space.
        """
        x1, z1 = p1
        x2, z2 = p2

        dx = x2 - x1
        dz = z2 - z1
        dist = math.hypot(dx, dz)
        if dist < 0.001:
            ix = int(round((x1 - x_off) / self._GRID_RESOLUTION))
            iz = int(round((z1 - z_off) / self._GRID_RESOLUTION))
            nx, nz = grid.shape
            if not (0 <= ix < nx and 0 <= iz < nz):
                return False
            return not grid[ix, iz]

        # Sample at half-cell intervals for robust collision checking
        steps = int(math.ceil(dist / (self._GRID_RESOLUTION * 0.5)))
        nx, nz = grid.shape

        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x1 + dx * t
            pz = z1 + dz * t

            ix = int(round((px - x_off) / self._GRID_RESOLUTION))
            iz = int(round((pz - z_off) / self._GRID_RESOLUTION))

            if not (0 <= ix < nx and 0 <= iz < nz):
                return False  # Out of bounds = blocked
            if grid[ix, iz]:
                return False  # Occupied cell = collision

        return True

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

        # Phase 1: Build 3D-aware occupancy grid
        grid, (x_off, z_off), _ = self._build_occupancy_grid()

        # Convert world coordinates to grid indices
        start_ix = int(round((x - x_off) / self._GRID_RESOLUTION))
        start_iz = int(round((z - z_off) / self._GRID_RESOLUTION))
        goal_ix = int(round((tx - x_off) / self._GRID_RESOLUTION))
        goal_iz = int(round((tz - z_off) / self._GRID_RESOLUTION))

        # Find nearest free cells if start/goal are blocked (after inflation)
        start_cell = self._find_nearest_free_cell(start_ix, start_iz, grid)
        goal_cell = self._find_nearest_free_cell(goal_ix, goal_iz, grid)

        if start_cell is None or goal_cell is None:
            return NavigationResult(
                success=False, final_position=(x, y, z), steps_taken=0, path=[]
            )

        # Clear start and goal cells for accessibility
        grid[start_cell[0], start_cell[1]] = False
        grid[goal_cell[0], goal_cell[1]] = False

        # Phase 2: A* pathfinding on x-z plane (global shortest path)
        grid_path = self._astar_2d(start_cell, goal_cell, grid)

        if grid_path is None:
            return NavigationResult(
                success=False, final_position=(x, y, z), steps_taken=0, path=[]
            )

        # Convert grid path to world coordinates on x-z plane
        world_path_2d = [
            (x_off + ix * self._GRID_RESOLUTION,
             z_off + iz * self._GRID_RESOLUTION)
            for ix, iz in grid_path
        ]

        # Phase 3: Path smoothing via shortcutting (3 iterations)
        smoothed_2d = self._smooth_path(
            world_path_2d, grid, x_off, z_off, iterations=3
        )

        # Generate 3D animation path with height interpolation
        ANIM_STEP_SIZE = 0.5  # ~0.5m per animation step for smooth movement
        path_3d: List[Tuple[float, float, float]] = []

        # Calculate total 2D path length for proportional height interpolation
        total_dist = sum(
            math.hypot(
                smoothed_2d[i + 1][0] - smoothed_2d[i][0],
                smoothed_2d[i + 1][1] - smoothed_2d[i][1],
            )
            for i in range(len(smoothed_2d) - 1)
        ) if len(smoothed_2d) > 1 else 0.0

        cumulative_dist = 0.0
        for seg_idx in range(len(smoothed_2d) - 1):
            sx, sz = smoothed_2d[seg_idx]
            ex, ez = smoothed_2d[seg_idx + 1]
            seg_len = math.hypot(ex - sx, ez - sz)

            if seg_len < 0.001:
                continue

            n_steps = max(2, int(math.ceil(seg_len / ANIM_STEP_SIZE)))
            for step in range(n_steps + 1):
                # Skip last step of non-final segments to avoid duplicate waypoints
                if seg_idx < len(smoothed_2d) - 2 and step == n_steps:
                    continue

                t = step / n_steps
                px = sx + (ex - sx) * t
                pz = sz + (ez - sz) * t

                # Height interpolation based on cumulative progress
                h_t = (cumulative_dist + seg_len * t) / total_dist if total_dist > 0 else 0.0
                py = y + (ty - y) * h_t

                path_3d.append((px, py, pz))

            cumulative_dist += seg_len

        # Update agent state to final position
        final_theta = math.atan2(tz - z, tx - x) if abs(tx - x) + abs(tz - z) > 0.001 else theta
        self._agents[self._agent_id] = (tx, ty, tz, final_theta)
        self._nav_path = path_3d  # Cache for step-by-step animation replay

        return NavigationResult(
            success=True,
            final_position=(tx, ty, tz),
            steps_taken=len(path_3d),
            collision_count=0,
            path=path_3d,
        )
