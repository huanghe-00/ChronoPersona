"""State machine orchestration for Agent Core."""

from typing import Optional

from chronopersona.contracts.interfaces import (
    AbstractAgentCore,
    AbstractMemoryStore,
    AbstractModelRouter,
)
from chronopersona.contracts.schemas import AgentOutput, EmbodiedState, EmotionState
from chronopersona.agent_core.intent_node import IntentNode
from chronopersona.agent_core.llm_node import LLMNode
from chronopersona.agent_core.memory_node import MemoryNode
from chronopersona.agent_core.output_node import OutputNode


class StateMachineAgentCore(AbstractAgentCore):
    """Agent core using state machine: Intent -> Memory -> LLM -> Output."""

    def __init__(
        self,
        memory_store: AbstractMemoryStore,
        model_router: AbstractModelRouter,
    ) -> None:
        self._memory_store = memory_store
        self._model_router = model_router
        self._intent_node = IntentNode()
        self._memory_node = MemoryNode(memory_store)
        self._llm_node = LLMNode(model_router)
        self._output_node = OutputNode()
        self._persona_id: str = "default"
        self._emotion_state: EmotionState = EmotionState()

    def run_turn(
        self,
        user_input: str,
        branch_id: str,
        embodied_state: Optional[EmbodiedState] = None,
    ) -> AgentOutput:
        """Execute one turn: classify intent, retrieve memory, generate, assemble."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        intent = self._intent_node.classify(user_input)
        context = self._memory_node.retrieve(user_input, branch_id, intent=intent.value)
        prompt = self._build_prompt(user_input, context)
        response = self._llm_node.generate(prompt, branch_id)
        return self._output_node.assemble(response, context, branch_id)

    def _build_prompt(self, user_input: str, context: object) -> str:
        """Build LLM prompt with retrieved context."""
        memories = "\n".join(f"- {m.content}" for m in context.episodic_memories[:3])
        if memories:
            return f"Context:\n{memories}\n\nUser: {user_input}\nAgent:"
        return f"User: {user_input}\nAgent:"

    def switch_persona(self, persona_id: str, branch_id: str) -> None:
        """Switch active persona."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._persona_id = persona_id

    def get_emotion_state(self) -> EmotionState:
        """Return current emotion state."""
        return self._emotion_state

    def get_memory_summary(self, branch_id: str) -> str:
        """Return a summary of memory state."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        ctx = self._memory_store.retrieve("", branch_id)
        return f"Working: {len(ctx.working_memories)}, Episodic: {len(ctx.episodic_memories)}"
