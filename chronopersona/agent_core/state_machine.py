"""State machine orchestration for Agent Core."""

import re
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
    MemoryEntry,
    RetrievedContext,
    Version,
)
from chronopersona.agent_core.intent_node import Intent, IntentNode
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

    # MVA prompt budget allocation (requirements.md 4.14.1)
    PROMPT_TOKEN_BUDGET: int = 4096
    BUDGET_L1_PCT: float = 0.40
    BUDGET_L2_PCT: float = 0.30
    BUDGET_L3_PCT: float = 0.20
    BUDGET_RESERVE_PCT: float = 0.10
    # Heuristic tokens per item for MVA truncation
    TOKENS_PER_EPISODIC: int = 150
    TOKENS_PER_FACT: int = 50
    TOKENS_PER_INSIGHT: int = 80

    def __init__(
        self,
        memory_store: AbstractMemoryStore,
        model_router: AbstractModelRouter,
        version_manager: Optional[AbstractVersionManager] = None,
        intent_graph: Optional[IntentGraph] = None,
        persona_injector: Optional[IPersonaInjector] = None,
        action_planner: Optional[AbstractActionPlanner] = None,
        embodied_adapter: Optional[Any] = None,
    ) -> None:
        self._memory_store = memory_store
        self._model_router = model_router
        self._version_manager = version_manager
        self._persona_injector = persona_injector
        self._action_planner = action_planner
        self._embodied_adapter = embodied_adapter
        self._intent_node = IntentNode()
        self._memory_node = MemoryNode(memory_store, intent_graph=intent_graph)
        self._llm_node = LLMNode(model_router)
        self._output_node = OutputNode()
        self._persona_id: str = "default"
        self._emotion_state: EmotionState = EmotionState()
        self._working_windows: Dict[str, WorkingMemoryWindow] = {}
        self._insight_scheduler: Optional[Any] = None
        self._turn_count: Dict[str, int] = {}
        self._token_budget: int = 8000  # MVA context budget (4K-8K upper bound)
        self._tokens_used: Dict[str, int] = {}

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

        # H1: Update emotion state before navigation, consistent with normal flow
        self._emotion_state = self._update_emotion(user_input, branch_id)

        # Embodied navigation: intent-driven bypass for semantic navigation
        if intent == Intent.NAVIGATION and self._embodied_adapter is not None:
            nav_target = self._extract_navigation_target(user_input)
            if nav_target:
                from chronopersona.contracts.schemas import SemanticNavigationGoal
                goal = SemanticNavigationGoal(target_object=nav_target)
                nav_result = self._embodied_adapter.navigate_to_object(goal)
                reply = (
                    f"已到达{nav_target}旁边，还需要什么？"
                    if nav_result.success
                    else f"无法找到{nav_target}，请确认目标名称。"
                )
                # Persist to L1 working memory
                window = self._get_or_create_window(branch_id)
                window.add_turn(user_input, reply, branch_id)

                # Persist navigation event to L2 episodic memory
                memory_entry = MemoryEntry(
                    content=f"[导航] 用户指令：'{user_input}' → 结果：{'成功' if nav_result.success else '失败'}，最终位置 {nav_result.final_position}",
                    branch_id=branch_id,
                    memory_type="episodic",
                    session_id="embodied_nav",
                    entities=[nav_target] if nav_result.success else [],
                    metadata={
                        "source": "embodied_navigation_bypass",
                        "nav_target": nav_target,
                        "final_position": nav_result.final_position,
                        "extraction_model": "heuristic_rule",
                        "extraction_confidence": 1.0,
                    },
                )
                try:
                    self._memory_store.add(memory_entry, branch_id=branch_id)
                except (ValueError, RuntimeError) as e:
                    logger.warning("Failed to persist navigation memory for branch {}: {}", branch_id, e)

                action_plan = None
                if nav_result.success:
                    from chronopersona.contracts.schemas import ActionPlan
                    action_plan = ActionPlan(
                        action_token="navigate_to_object",
                        action_params={
                            "target": nav_target,
                            "final_position": nav_result.final_position,
                        },
                        reasoning=f"Navigation to '{nav_target}' succeeded",
                    )

                return AgentOutput(
                    reply_text=reply,
                    emotion_state=self._emotion_state,
                    action_plan=action_plan,
                    used_memories=[],
                    branch_id=branch_id,
                )

        # v1.1.0: Hard budget throttle (production baseline skeleton)
        used = self._tokens_used.get(branch_id, 0)
        if used >= self._token_budget:
            logger.warning(
                "Token budget exceeded for branch {}: {}/{}",
                branch_id, used, self._token_budget,
            )
            return AgentOutput(
                reply_text="当前会话 token 预算已用尽，请开启新会话。",
                emotion_state=self._emotion_state,
                action_plan=None,
                used_memories=[],
                branch_id=branch_id,
            )

        context = self._memory_node.retrieve(user_input, branch_id, intent=intent.value)

        # Emotion already updated at top of run_turn; avoid double computation
        prompt = self._build_prompt(user_input, context, branch_id, embodied_state)
        response = self._llm_node.generate(prompt, branch_id)

        # v1.1.0: Budget accumulation and tiered alerting
        turn_tokens = response.input_tokens + response.output_tokens
        self._tokens_used[branch_id] = used + turn_tokens
        if self._tokens_used[branch_id] >= self._token_budget:
            logger.error(
                "Token budget exhausted after this turn: {}/{}",
                self._tokens_used[branch_id], self._token_budget,
            )
        elif self._tokens_used[branch_id] >= int(self._token_budget * 0.8):
            logger.warning(
                "Token budget warning: {}/{} (80% threshold)",
                self._tokens_used[branch_id], self._token_budget,
            )

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

        output = self._output_node.assemble(
            response, context, branch_id, self._emotion_state
        )
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
        l1_limit = int(self.PROMPT_TOKEN_BUDGET * self.BUDGET_L1_PCT)
        l1_items = window.get_context(branch_id=branch_id, token_limit=l1_limit)

        l1_parts: List[str] = []
        for item in l1_items:
            if isinstance(item, TurnEntry):
                l1_parts.append(item.to_text())
            elif isinstance(item, CompressedSummary):
                l1_parts.append(item.content)

        l1_text = "\n".join(l1_parts)

        l2_limit_tokens = int(self.PROMPT_TOKEN_BUDGET * self.BUDGET_L2_PCT)
        max_l2 = max(1, l2_limit_tokens // self.TOKENS_PER_EPISODIC)
        l2_text = "\n".join(f"- {m.content}" for m in context.episodic_memories[:max_l2])

        l3_limit_tokens = int(self.PROMPT_TOKEN_BUDGET * self.BUDGET_L3_PCT)
        max_facts = max(1, int(l3_limit_tokens * 0.6) // self.TOKENS_PER_FACT)
        max_insights = max(1, int(l3_limit_tokens * 0.4) // self.TOKENS_PER_INSIGHT)
        l3_facts = "\n".join(
            f"- {f.attribute}: {f.value}" for f in context.semantic_facts[:max_facts]
        )
        l3_insights = "\n".join(
            f"- {i}" for i in context.insights[:max_insights]
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

    def get_embodied_state(self) -> Optional[EmbodiedState]:
        """Return current embodied state from adapter, or None if not configured."""
        if self._embodied_adapter is None:
            return None
        try:
            return self._embodied_adapter.get_perception("default")
        except (ValueError, RuntimeError) as e:
            logger.warning("Failed to get embodied state: {}", e)
            return None

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
                valence=-0.7,
                arousal=0.6,
            )
        if any(w in text for w in positive_words):
            return EmotionState(
                current_state=EmotionLabel.EMPATHETIC,
                intensity=0.5,
                trigger_reason="User expressed positive emotion",
                confidence=0.9,
                valence=0.6,
                arousal=0.4,
            )
        return EmotionState(
            current_state=EmotionLabel.NEUTRAL,
            intensity=0.0,
            confidence=0.5,
            valence=0.0,
            arousal=0.0,
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

    def _extract_navigation_target(self, text: str) -> Optional[str]:
        """Heuristic extraction of navigation target from user input."""
        patterns = [
            r"(?:到|去|导航到|前往|走向)\s*(\S+?)(?:旁边|附近|那里|去)?[吧]?[？?]?\s*$",
            r"(?:请|帮我)?\s*(?:到|去|导航到)\s*(\S+?)(?:旁边|附近|那里)?\s*[吧]?[？?]?\s*$",
            r"(?:靠近|走近)\s*(\S+?)(?:旁边|附近)?\s*$",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip()
        return None
