"""Mock implementation of AbstractAgentCore."""

from typing import Optional

from chronopersona.contracts.interfaces import AbstractAgentCore
from chronopersona.contracts.schemas import (
    ActionPlan,
    AgentOutput,
    EmbodiedState,
    EmotionLabel,
    EmotionState,
)


class MockAgentCore(AbstractAgentCore):
    """Mock agent core for testing."""

    def __init__(self) -> None:
        self._emotion = EmotionState(
            current_state=EmotionLabel.NEUTRAL,
            intensity=0.0,
            trigger_reason="",
            state_since="",
        )
        self._persona_id = "default"
        self._branch_id = "main"

    def run_turn(
        self,
        user_input: str,
        branch_id: str,
        embodied_state: Optional[EmbodiedState] = None,
    ) -> AgentOutput:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._branch_id = branch_id
        return AgentOutput(
            reply_text=f"[Mock] Echo: {user_input}",
            action_plan=None,
            emotion_state=self._emotion,
            used_memories=[],
            branch_id=branch_id,
        )

    def switch_persona(self, persona_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._persona_id = persona_id
        self._branch_id = branch_id

    def get_emotion_state(self) -> EmotionState:
        return self._emotion

    def get_memory_summary(self, branch_id: str) -> str:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return f"[Mock] Memory summary for branch {branch_id}"
