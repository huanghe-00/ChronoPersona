"""Output assembly node."""

from chronopersona.contracts.schemas import (
    AgentOutput,
    EmotionLabel,
    EmotionState,
    ModelResponse,
    RetrievedContext,
)


class OutputNode:
    """Assembles final AgentOutput from model response and context."""

    def assemble(
        self,
        response: ModelResponse,
        context: RetrievedContext,
        branch_id: str,
    ) -> AgentOutput:
        """Build AgentOutput with emotion state and used memory references."""
        return AgentOutput(
            reply_text=response.content,
            emotion_state=EmotionState(
                current_state=EmotionLabel.NEUTRAL,
                intensity=0.5,
            ),
            used_memories=[m.id for m in context.episodic_memories if m.id],
            branch_id=branch_id,
        )
