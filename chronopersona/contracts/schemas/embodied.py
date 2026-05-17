"""Embodied schemas for perception and action."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
