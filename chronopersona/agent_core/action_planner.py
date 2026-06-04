"""ActionPlanner implementation with VAD-aware modulation.

v0.7.0: Integrates EmotionState.valence and .arousal into
the EMOTION_BEHAVIOR_MODULATION table for fine-grained
speed/volume/proximity adjustments.
"""

import re
from typing import Dict

from loguru import logger

from chronopersona.contracts.interfaces import AbstractActionPlanner
from chronopersona.contracts.schemas import ActionPlan, EmotionState


class ActionPlanner(AbstractActionPlanner):
    """Parse action tokens and apply emotion modulation."""

    EMOTION_MODULATION: Dict[str, Dict[str, float]] = {
        "NEUTRAL": {"speed_mult": 1.0, "volume_mult": 1.0, "proximity_mult": 1.0},
        "CURIOUS": {"speed_mult": 1.2, "volume_mult": 1.0, "proximity_mult": 0.8},
        "EMPATHETIC": {"speed_mult": 0.7, "volume_mult": 0.9, "proximity_mult": 0.7},
        "CONCERNED": {"speed_mult": 0.5, "volume_mult": 0.8, "proximity_mult": 0.5},
        "REFLECTIVE": {"speed_mult": 0.3, "volume_mult": 0.7, "proximity_mult": 1.5},
    }

    ACTION_PATTERNS = [
        (r"(?:慢慢|轻轻|温柔).*(?:靠近|接近)", "approach_gently", {"speed": 0.5}),
        (r"(?:后退|退后|远离)", "retreat_slowly", {"speed": 0.5}),
        (r"(?:转身|转向).*(?:用户|人)", "turn_to_user", {}),
        (r"(?:互动|交互|操作)", "interact", {}),
        (r"(?:环顾|看看|观察)", "look_around", {}),
    ]

    def plan(
        self,
        llm_output_text: str,
        emotion_state: EmotionState,
        branch_id: str,
    ) -> ActionPlan:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        action_token, params, reasoning = self._parse_action(llm_output_text)
        modulation = self._get_modulation(emotion_state)

        logger.info(
            "ActionPlanner: token={} emotion={} branch={}",
            action_token,
            emotion_state.current_state,
            branch_id,
        )

        return ActionPlan(
            action_token=action_token,
            action_params={**params, **modulation},
            reasoning=reasoning,
        )

    def _parse_action(self, text: str) -> tuple[str, Dict[str, float], str]:
        for pattern, token, default_params in self.ACTION_PATTERNS:
            if re.search(pattern, text):
                return token, default_params, f"Matched pattern '{pattern}' in LLM output"
        return "idle", {}, "No action pattern matched, defaulting to idle"

    def _get_modulation(self, emotion_state: EmotionState) -> Dict[str, float]:
        base = self.EMOTION_MODULATION.get(
            emotion_state.current_state.value,
            self.EMOTION_MODULATION["NEUTRAL"],
        )
        # NEUTRAL is the baseline state; modulation factors are not scaled by intensity
        if emotion_state.current_state.value == "NEUTRAL":
            return dict(base)
        
        # Non-NEUTRAL states scale by intensity (higher intensity = more pronounced modulation)
        intensity = max(0.1, min(1.0, emotion_state.intensity))
        return {k: v * intensity for k, v in base.items()}
"""ActionPlanner with VAD-based emotion modulation.

v0.7.0: Integrates EmotionState.valence and .arousal into
the EMOTION_BEHAVIOR_MODULATION table for fine-grained
speed/volume/proximity adjustments.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from chronopersona.contracts.schemas.agent import EmotionState


@dataclass
class ActionPlan:
    """Structured action plan with reasoning."""
    action_token: str = ""
    action_params: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


# Base modulation table (requirements.md 4.7)
EMOTION_BEHAVIOR_MODULATION = {
    "NEUTRAL":    {"speed_mult": 1.0, "volume_mult": 1.0, "proximity_mult": 1.0},
    "CURIOUS":    {"speed_mult": 1.2, "volume_mult": 1.0, "proximity_mult": 0.8},
    "EMPATHETIC": {"speed_mult": 0.7, "volume_mult": 0.9, "proximity_mult": 0.7},
    "CONCERNED":  {"speed_mult": 0.5, "volume_mult": 0.8, "proximity_mult": 0.5},
    "REFLECTIVE": {"speed_mult": 0.3, "volume_mult": 0.7, "proximity_mult": 1.2},
}


class ActionPlanner:
    """Plans actions with VAD-modulated behavior parameters."""

    def plan(
        self,
        action_token: str,
        base_params: Optional[Dict[str, float]] = None,
        emotion: Optional[EmotionState] = None,
        reasoning: str = "",
    ) -> ActionPlan:
        """Create an ActionPlan with VAD-adjusted parameters.

        Args:
            action_token: High-level action token (e.g., 'approach_gently').
            base_params: Base parameters for the action (speed, proximity, etc.).
            emotion: Current EmotionState (including valence/arousal).
            reasoning: Human-readable explanation for the action.

        Returns:
            ActionPlan with modulated parameters.
        """
        params = dict(base_params) if base_params else {}

        # Apply base modulation from emotion label
        if emotion is not None:
            label = emotion.current_state.value if hasattr(emotion.current_state, "value") else str(emotion.current_state)
            mod = EMOTION_BEHAVIOR_MODULATION.get(label, EMOTION_BEHAVIOR_MODULATION["NEUTRAL"])
            params.setdefault("speed_mult", mod["speed_mult"])
            params.setdefault("volume_mult", mod["volume_mult"])
            params.setdefault("proximity_mult", mod["proximity_mult"])

            # VAD fine-tuning (v0.7.0)
            # Arousal increases speed and reduces proximity (more urgent)
            arousal = max(0.0, min(1.0, emotion.arousal))
            if arousal > 0.5:
                arousal_factor = 1.0 + (arousal - 0.5) * 0.4  # up to +20%
                params["speed_mult"] = params.get("speed_mult", 1.0) * arousal_factor
                params["proximity_mult"] = params.get("proximity_mult", 1.0) * (1.0 - (arousal - 0.5) * 0.3)

            # Valence modulates volume: positive -> slightly louder, negative -> softer
            valence = max(-1.0, min(1.0, emotion.valence))
            if valence > 0.3:
                params["volume_mult"] = params.get("volume_mult", 1.0) * (1.0 + valence * 0.1)
            elif valence < -0.3:
                params["volume_mult"] = params.get("volume_mult", 1.0) * (1.0 + valence * 0.15)

        return ActionPlan(
            action_token=action_token,
            action_params=params,
            reasoning=reasoning,
        )
