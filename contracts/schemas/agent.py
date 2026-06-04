"""Agent-related data schemas for ChronoPersona.

Defines EmotionState with VAD (Valence-Arousal) extensions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EmotionLabel(str, Enum):
    NEUTRAL = "NEUTRAL"
    CURIOUS = "CURIOUS"
    EMPATHETIC = "EMPATHETIC"
    CONCERNED = "CONCERNED"
    REFLECTIVE = "REFLECTIVE"


@dataclass
class EmotionState:
    """Emotion state with VAD (Valence-Arousal) extensions.

    v0.7.0: Added valence and arousal fields for fine-grained
    behavior modulation. Dominance dimension intentionally omitted
    (low ROI in Companion scenarios).
    """

    current_state: EmotionLabel = EmotionLabel.NEUTRAL
    intensity: float = 0.0  # 0.0 ~ 1.0
    trigger_reason: str = ""
    state_since: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.5

    # v0.7.0 VAD extensions
    valence: float = 0.0  # -1.0 (negative) ~ +1.0 (positive)
    arousal: float = 0.0  # 0.0 (calm) ~ 1.0 (excited/urgent)
