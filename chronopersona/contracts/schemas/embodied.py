"""Embodied perception and action translation schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PerceptionResult:
    """Result of executing an action in the embodied environment.

    Attributes:
        success: Whether the action was executed successfully.
        new_state: Optional updated EmbodiedState after execution.
        observation: Human-readable observation text.
        metadata: Execution metadata.
    """

    success: bool = False
    new_state: Optional[Any] = None
    observation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialRecord:
    """Spatial memory record for embodied navigation.

    Attributes:
        location: Semantic location name (e.g. "kitchen").
        coordinates: Numeric coordinates {x, y, theta}.
        objects: Objects observed at this location.
        timestamp: ISO-8601 timestamp.
    """

    location: str = ""
    coordinates: Dict[str, float] = field(default_factory=dict)
    objects: List[str] = field(default_factory=list)
    timestamp: str = ""


@dataclass
class LowLevelCommand:
    """Translated low-level robot command.

    Attributes:
        robot_type: Target platform (grid_2d, ros2_mobile, mujoco).
        command: Low-level command string.
        params: Command parameters.
    """

    robot_type: str = ""
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
