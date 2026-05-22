"""State machine orchestration for Agent Core."""

from typing import Any, Optional

from loguru import logger

from chronopersona.contracts.interfaces import (
    AbstractAgentCore,
    AbstractMemoryStore,
    AbstractModelRouter,
    AbstractVersionManager,
    IPersonaInjector,
)
from chronopersona.contracts.schemas import (
    AgentOutput,
    ChangeSet,
    EmbodiedState,
    EmotionState,
    RetrievedContext,
    Version,
)
from chronopersona.agent_core.intent_node import IntentNode
from chronopersona.agent_core.llm_node import LLMNode
from chronopersona.agent_core.memory_node import MemoryNode
from chronopersona.agent_core.output_node import OutputNode
from chronopersona.memory_system.l1_working.sliding_window import (
    CompressedSummary,
    TurnEntry,
    WorkingMemoryWindow,
)
from chronopersona.memory_system.l3_semantic import IntentGraph


class StateMachineAgentCore(AbstractAgentCore):
    """Agent core using state machine: Intent -> Memory -> LLM -> Output."""

    def __init__(
        self,
        memory_store: AbstractMemoryStore,
        model_router: AbstractModelRouter,
        version_manager: AbstractVersionManager | None = None,
        intent_graph: IntentGraph | None = None,
        persona_injector: IPersonaInjector | None = None,
        action_planner: Any | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._model_router = model_router
        self._version_manager = version_manager
        self._persona_injector = persona_injector
        self._action_planner = action_planner
        self._intent_node = IntentNode()
        self._memory_node = MemoryNode(memory_store, intent_graph=intent_graph)
        self._llm_node = LLMNode(model_router)
        self._output_node = OutputNode()
        self._persona_id: str = "default"
        self._emotion_state: EmotionState = EmotionState()
        self._working_windows: dict[str, WorkingMemoryWindow] = {}
        self._insight_scheduler: Any | None = None
        self._turn_count: dict[str, int] = {}

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
        prompt = self._build_prompt(user_input, context, branch_id)
        response = self._llm_node.generate(prompt, branch_id)

        # W5: ActionPlanner parses action intent and applies emotion modulation
        action_plan = None
        if self._action_planner is not None:
            try:
                action_plan = self._action_planner.plan(
                    response.content,
                    emotion_state=self.get_emotion_state(),
                    branch_id=branch_id,
                )
            except Exception:
                logger.warning("ActionPlanner failed for branch {}", branch_id)

        output = self._output_node.assemble(response, context, branch_id)
        if action_plan is not None:
            output.action_plan = action_plan

        # Persist turn to L1 Working Memory
        window = self._get_or_create_window(branch_id)
        window.add_turn(user_input, output.reply_text, branch_id)

        # W4: Trigger InsightScheduler every N turns
        if self._insight_scheduler is not None:
            self._turn_count[branch_id] = self._turn_count.get(branch_id, 0) + 1
            try:
                self._insight_scheduler.maybe_trigger(
                    branch_id, self._turn_count[branch_id]
                )
            except Exception:
                logger.warning(
                    "InsightScheduler trigger failed for branch {}", branch_id
                )

        return output

    def _build_prompt(self, user_input: str, context: RetrievedContext, branch_id: str) -> str:
        """Build LLM prompt with L1 working memory and L2/L3 retrieved context."""
        window = self._get_or_create_window(branch_id)
        l1_items = window.get_context(branch_id=branch_id, token_limit=2048)

        l1_parts: list[str] = []
        for item in l1_items:
            if isinstance(item, TurnEntry):
                l1_parts.append(item.to_text())
            elif isinstance(item, CompressedSummary):
                l1_parts.append(item.content)

        l1_text = "\n".join(l1_parts)
        l2_text = "\n".join(f"- {m.content}" for m in context.episodic_memories[:3])

        parts: list[str] = []
        if l1_text:
            parts.append(f"[Recent Conversation]\n{l1_text}")
        if l2_text:
            parts.append(f"[Retrieved Memories]\n{l2_text}")

        context_text = "\n\n".join(parts)
        if context_text:
            return f"{context_text}\n\nUser: {user_input}\nAgent:"
        return f"User: {user_input}\nAgent:"

    def switch_persona(self, persona_id: str, branch_id: str) -> None:
        """Switch active persona with eject → snapshot → inject."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if self._persona_injector is not None:
            self._persona_injector.eject(self._persona_id, branch_id)
        if self._version_manager is not None:
            self._version_manager.commit(branch_id, ChangeSet())
        self._persona_id = persona_id
        if self._persona_injector is not None:
            self._persona_injector.inject(persona_id, branch_id, self)

    def _get_or_create_window(self, branch_id: str, session_id: str = "default") -> WorkingMemoryWindow:
        """Get or create L1 WorkingMemoryWindow for the branch."""
        if branch_id not in self._working_windows:
            self._working_windows[branch_id] = WorkingMemoryWindow(
                branch_id=branch_id,
                session_id=session_id,
            )
        return self._working_windows[branch_id]

    def commit_session_snapshot(self, branch_id: str) -> Version:
        """Commit a Session-MVCC snapshot for the given branch."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if self._version_manager is None:
            raise RuntimeError("version_manager not configured")
        return self._version_manager.commit(branch_id, ChangeSet())

    def get_emotion_state(self) -> EmotionState:
        """Return current emotion state."""
        return self._emotion_state

    def set_insight_scheduler(self, scheduler: Any) -> None:
        """Attach InsightScheduler for periodic consolidation."""
        self._insight_scheduler = scheduler

    def get_memory_summary(self, branch_id: str) -> str:
        """Return a summary of memory state."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        ctx = self._memory_store.retrieve("", branch_id)
        return f"Working: {len(ctx.working_memories)}, Episodic: {len(ctx.episodic_memories)}"
