"""State machine orchestration for Agent Core."""

from typing import Any, Dict, List, Optional

from loguru import logger

from chronopersona.contracts.interfaces import (
    AbstractActionPlanner,
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
    EmotionLabel,
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
        version_manager: Optional[AbstractVersionManager] = None,
        intent_graph: Optional[IntentGraph] = None,
        persona_injector: Optional[IPersonaInjector] = None,
        action_planner: Optional[AbstractActionPlanner] = None,
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
        self._working_windows: Dict[str, WorkingMemoryWindow] = {}
        self._insight_scheduler: Optional[Any] = None
        self._turn_count: Dict[str, int] = {}

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

        # H1: Update emotion state BEFORE building prompt so LLM sees latest emotion
        self._emotion_state = self._update_emotion(user_input, branch_id)

        prompt = self._build_prompt(user_input, context, branch_id, embodied_state)
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
            except (ValueError, RuntimeError) as e:
                logger.warning("ActionPlanner failed for branch {}: {}", branch_id, e)

        output = self._output_node.assemble(response, context, branch_id)

        output.emotion_state = self._emotion_state
        if action_plan is not None:
            output.action_plan = action_plan
            output.emotion_modulation = action_plan.action_params

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
            except (ValueError, RuntimeError) as e:
                logger.warning(
                    "InsightScheduler trigger failed for branch {}: {}", branch_id, e
                )

        return output

    def _build_prompt(
        self,
        user_input: str,
        context: RetrievedContext,
        branch_id: str,
        embodied_state: Optional[EmbodiedState] = None,
    ) -> str:
        """Build LLM prompt with L1 working memory and L2/L3 retrieved context."""
        window = self._get_or_create_window(branch_id)
        l1_items = window.get_context(branch_id=branch_id, token_limit=2048)

        l1_parts: List[str] = []
        for item in l1_items:
            if isinstance(item, TurnEntry):
                l1_parts.append(item.to_text())
            elif isinstance(item, CompressedSummary):
                l1_parts.append(item.content)

        l1_text = "\n".join(l1_parts)
        l2_text = "\n".join(f"- {m.content}" for m in context.episodic_memories[:3])

        l3_facts = "\n".join(
            f"- {f.attribute}: {f.value}" for f in context.semantic_facts[:3]
        )
        l3_insights = "\n".join(
            f"- {i}" for i in context.insights[:2]
        )

        parts: List[str] = []
        if embodied_state is not None:
            fov = ", ".join(embodied_state.fov_objects) if embodied_state.fov_objects else "none"
            parts.append(
                f"[Embodied State] Agent at ({embodied_state.x}, {embodied_state.y}), "
                f"facing {embodied_state.theta:.2f} rad. FOV: {fov}"
            )
        if self._emotion_state is not None:
            if (
                self._emotion_state.current_state != EmotionLabel.NEUTRAL
                and self._emotion_state.confidence >= 0.7
            ):
                parts.append(
                    f"[Emotion State] {self._emotion_state.current_state.value} "
                    f"(intensity={self._emotion_state.intensity:.1f})"
                )
        if l1_text:
            parts.append(f"[Recent Conversation]\n{l1_text}")
        if l2_text:
            parts.append(f"[Retrieved Memories]\n{l2_text}")
        if l3_facts:
            parts.append(f"[Semantic Facts]\n{l3_facts}")
        if l3_insights:
            parts.append(f"[Insights]\n{l3_insights}")

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

    def _update_emotion(self, user_input: str, branch_id: str) -> EmotionState:
        """T0 rule-based emotion classification with confidence.

        Args:
            user_input: The user's input text.
            branch_id: Explicit branch identifier (reserved for future per-branch isolation).

        Returns:
            Updated EmotionState.
        """
        text = user_input.lower()
        negative_words = ["难过", "伤心", "痛苦", "焦虑", "担心", "害怕"]
        positive_words = ["开心", "高兴", "兴奋", "喜欢", "谢谢", "好"]
        if any(w in text for w in negative_words):
            return EmotionState(
                current_state=EmotionLabel.CONCERNED,
                intensity=0.7,
                trigger_reason="User expressed negative emotion",
                confidence=0.9,
            )
        if any(w in text for w in positive_words):
            return EmotionState(
                current_state=EmotionLabel.EMPATHETIC,
                intensity=0.5,
                trigger_reason="User expressed positive emotion",
                confidence=0.9,
            )
        return EmotionState(
            current_state=EmotionLabel.NEUTRAL,
            intensity=0.0,
            confidence=0.5,
        )

    def get_memory_summary(self, branch_id: str) -> str:
        """Return a summary of memory state."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        window = self._get_or_create_window(branch_id)
        parts: List[str] = []
        parts.append(f"Working: {len(window._turns)} turns")
        parts.append("Episodic: retrieved via memory node")
        return "\n".join(parts)
