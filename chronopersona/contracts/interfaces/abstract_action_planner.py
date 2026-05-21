"""Abstract interface for ActionPlanner."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from chronopersona.contracts.schemas import ActionPlan, EmotionState


class AbstractActionPlanner(ABC):
    """Parse high-level action intent from LLM output and assemble ActionPlan.

    Positioned between LLM Node and Output Node in the Agent Core pipeline.
    """

    @abstractmethod
    def plan(
        self,
        llm_output_text: str,
        emotion_state: EmotionState,
        branch_id: str,
    ) -> ActionPlan:
        """Extract action_token and apply emotion modulation.

        Args:
            llm_output_text: Raw text from LLM (may contain action intent).
            emotion_state: Current emotional state for modulation lookup.
            branch_id: Explicit branch isolation.

        Returns:
            ActionPlan with action_token, params, reasoning, and modulation.

        Raises:
            ValueError: If branch_id is empty.
        """
