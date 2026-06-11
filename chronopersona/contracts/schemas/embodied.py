"""Embodied schemas for perception and action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SpatialRecord:
    """A spatial memory record for an object in the environment.

    Attributes:
        object_id: Unique identifier of the object.
        x: x-coordinate.
        y: y-coordinate.
        metadata: Additional unstructured metadata.
    """

    object_id: str = ""
    x: float = 0.0
    y: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LowLevelCommand:
    """Low-level command for a specific robot type.

    Attributes:
        robot_type: The target robot type (e.g., 'grid_2d').
        command: The command string.
        params: Command parameters.
    """

    robot_type: str = ""
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerceptionResult:
    """Result of executing an action.

    Attributes:
        success: Whether the action succeeded.
        message: Optional human-readable message.
    """

    success: bool = False
    message: str = ""


@dataclass
class VisualObservation:
    """First-person visual perception from embodied sensor suite.

    Attributes:
        rgb: RGB image array or None if unavailable.
        depth: Depth map or None.
        semantic_mask: Semantic segmentation mask or None.
    """

    rgb: Optional[Any] = None
    depth: Optional[Any] = None
    semantic_mask: Optional[Any] = None


@dataclass
class RobotState3D:
    """Proprioceptive state in 3D continuous space.

    Attributes:
        position: (x, y, z) coordinates.
        rotation: Rotation representation (e.g., quaternion or matrix).
        joint_positions: Optional joint angles for manipulators.
    """

    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Optional[Any] = None
    joint_positions: Optional[List[float]] = None


@dataclass
class SemanticNavigationGoal:
    """Natural-language navigation target resolved to semantic object.

    Attributes:
        target_object: Target object name (e.g., "sofa", "床").
        target_room: Optional room constraint (e.g., "living_room").
    """

    target_object: str = ""
    target_room: Optional[str] = None


@dataclass
class NavigationResult:
    """Outcome of a semantic navigation episode.

    Attributes:
        success: Whether the robot reached the target.
        final_position: Final (x, y, z).
        collision_count: Number of collisions during navigation.
        steps_taken: Number of simulation steps consumed.
        path: Waypoint sequence from start to final_position.
    """

    success: bool = False
    final_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    collision_count: int = 0
    steps_taken: int = 0
    path: List[Tuple[float, float, float]] = field(default_factory=list)
