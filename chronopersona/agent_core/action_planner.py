"""ActionPlanner implementation."""

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
