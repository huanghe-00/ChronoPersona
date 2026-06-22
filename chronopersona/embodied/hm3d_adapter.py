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

        # 收集所有碰撞障碍物，按路径中点距离排序（最关键优先）
        collisions = []
        for ox, oy, oz, radius in self._OBSTACLES:
            dist = self._point_to_segment_distance(ox, oz, x, z, tx, tz)
            if dist < radius:
                mid_x, mid_z = (x + tx) / 2.0, (z + tz) / 2.0
                mid_dist = math.hypot(ox - mid_x, oz - mid_z)
                collisions.append((mid_dist, ox, oy, oz, radius))

        # 最多处理前2个障碍，生成最多3段折线
        detour_points: List[Tuple[float, float]] = []
        if collisions:
            collisions.sort(key=lambda c: c[0])
            for idx in range(min(2, len(collisions))):
                _, ox, oy, oz, radius = collisions[idx]
                dx, dz = tx - x, tz - z
                norm = math.hypot(dx, dz)
                if norm > 0.001:
                    perp_x, perp_z = -dz / norm, dx / norm
                    # 基于当前线段起点（考虑已添加的绕行点）计算中点
                    seg_start_x = x if not detour_points else detour_points[-1][0]
                    seg_start_z = z if not detour_points else detour_points[-1][1]
                    mid_x = (seg_start_x + tx) / 2.0
                    mid_z = (seg_start_z + tz) / 2.0
                    off = radius + 2.0  # 更大偏移确保避开复杂障碍
                    dist_plus = math.hypot(
                        mid_x + perp_x * off - ox, mid_z + perp_z * off - oz
                    )
                    dist_minus = math.hypot(
                        mid_x - perp_x * off - ox, mid_z - perp_z * off - oz
                    )
                    if dist_plus > dist_minus:
                        detour_x, detour_z = mid_x + perp_x * off, mid_z + perp_z * off
                    else:
                        detour_x, detour_z = mid_x - perp_x * off, mid_z - perp_z * off
                    detour_points.append((detour_x, detour_z))

        # 生成多段折线路径
        path: List[Tuple[float, float, float]] = []
        waypoints = [(x, z)] + detour_points + [(tx, tz)]
        segments = len(waypoints) - 1
        steps_per_segment = 5 if segments > 1 else 10
        steps_taken = segments * steps_per_segment

        for seg_idx in range(segments):
            sx, sz = waypoints[seg_idx]
            ex, ez = waypoints[seg_idx + 1]
            for i in range(steps_per_segment + 1):
                if seg_idx < segments - 1 and i == steps_per_segment:
                    continue  # 避免中间节点重复
                t = i / steps_per_segment
                px = sx + (ex - sx) * t
                # y高度按整体进度线性插值
                overall_t = (seg_idx * steps_per_segment + i) / steps_taken
                py = y + (ty - y) * overall_t
                pz = sz + (ez - sz) * t
                path.append((px, py, pz))

        # Update agent state to final position
        final_theta = math.atan2(tz - z, tx - x)
        self._agents[self._agent_id] = (tx, ty, tz, final_theta)
        self._nav_path = path  # Cache for step-by-step animation replay
        return NavigationResult(
            success=True,
            final_position=(tx, ty, tz),
            steps_taken=steps_taken,
            collision_count=0,
            path=path,
        )
