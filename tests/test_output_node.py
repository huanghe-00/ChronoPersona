"""Unit tests for OutputNode."""

import pytest

from chronopersona.agent_core.output_node import OutputNode
from chronopersona.contracts.schemas import (
    AgentOutput,
    EmotionLabel,
    EmotionState,
    MemoryEntry,
    ModelResponse,
    RetrievedContext,
)


class TestOutputNode:
    """T01-T03: OutputNode assembly tests."""

    def test_assemble_basic(self) -> None:
        """T01: Assemble produces AgentOutput with reply text and branch_id."""
        node = OutputNode()
        response = ModelResponse(content="Hello user", model_name="mock")
        context = RetrievedContext(episodic_memories=[], total_tokens=0)
        out = node.assemble(response, context, "main")
        assert isinstance(out, AgentOutput)
        assert out.reply_text == "Hello user"
        assert out.branch_id == "main"

    def test_assemble_uses_passed_emotion_state(self) -> None:
        """T02: Emotion state from caller is preserved, not hard-coded default."""
        node = OutputNode()
        response = ModelResponse(content="reply", model_name="mock")
        context = RetrievedContext(episodic_memories=[], total_tokens=0)
        emotion = EmotionState(
            current_state=EmotionLabel.CONCERNED,
            intensity=0.8,
        )
        out = node.assemble(response, context, "main", emotion)
        assert out.emotion_state.current_state == EmotionLabel.CONCERNED
        assert out.emotion_state.intensity == 0.8

    def test_assemble_defaults_neutral_when_no_emotion(self) -> None:
        """T03: Falls back to NEUTRAL default when emotion_state is omitted."""
        node = OutputNode()
        response = ModelResponse(content="reply", model_name="mock")
        context = RetrievedContext(episodic_memories=[], total_tokens=0)
        out = node.assemble(response, context, "main")
        assert out.emotion_state.current_state == EmotionLabel.NEUTRAL
        assert out.emotion_state.intensity == 0.5
