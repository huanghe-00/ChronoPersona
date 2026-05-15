"""
Agent-related data schemas for ChronoPersona.

Defines the core data structures used by the Agent Core layer,
including emotion state, agent output, and embodied perception state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EmotionLabel(str, Enum):
    """Enumeration of possible emotion states."""

    NEUTRAL = "NEUTRAL"
    CURIOUS = "CURIOUS"
    EMPATHETIC = "EMPATHETIC"
    CONCERNED = "CONCERNED"
    REFLECTIVE = "REFLECTIVE"


@dataclass
class EmotionState:
    """Current emotional state of the agent.

    Attributes:
        current_state: The active emotion label.
        intensity: Continuous intensity value in [0.0, 1.0].
        trigger_reason: Human-readable reason for the current state.
        state_since: ISO-8601 timestamp when this state was entered.
    """

    current_state: EmotionLabel = EmotionLabel.NEUTRAL
    intensity: float = 0.0
    trigger_reason: str = ""
    state_since: str = ""


@dataclass
class ActionPlan:
    """Structured action plan produced by the ActionPlanner node.

    Attributes:
        action_token: High-level action token (e.g. "approach_gently").
        action_params: Parameters for the action (e.g. speed, proximity).
        reasoning: Human-readable explanation for the chosen action.
    """

    action_token: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class AgentOutput:
    """Complete output of a single agent turn.

    Attributes:
        reply_text: Natural language reply to the user.
        action_plan: Optional structured action plan for embodied execution.
        emotion_modulation: Optional modulation parameters (e.g. speed_mult, volume_mult).
        emotion_state: The agent's emotion state after processing the turn.
        used_memories: List of memory IDs referenced during generation.
        branch_id: The branch under which this turn was executed.
    """

    reply_text: str = ""
    action_plan: Optional[ActionPlan] = None
    emotion_modulation: Optional[Dict[str, float]] = None
    emotion_state: EmotionState = field(default_factory=EmotionState)
    used_memories: List[str] = field(default_factory=list)
    branch_id: str = ""


@dataclass
class EmbodiedState:
    """Perception snapshot from the 2D virtual environment.

    Attributes:
        x: Agent x-coordinate.
        y: Agent y-coordinate.
        theta: Agent orientation in radians.
        fov_objects: List of object identifiers currently in the field of view.
    """

    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    fov_objects: List[str] = field(default_factory=list)
