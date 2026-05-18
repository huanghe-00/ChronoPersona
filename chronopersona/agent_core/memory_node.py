"""Memory retrieval node."""

from dataclasses import replace
from typing import Optional

from chronopersona.contracts.interfaces import AbstractMemoryStore
from chronopersona.contracts.schemas import RetrievedContext
from chronopersona.memory_system.l3_semantic import IntentGraph, IntentNavigator


class MemoryNode:
    """Retrieves context from L1/L2/L3 memory layers."""

    _VALID_INTENTS: frozenset[str] = frozenset({
        "retrieve",
        "vertical_generalize",
        "vertical_specify",
        "parallel_compare",
        "temporal_trace",
        "causal_explore",
        "empathize",
        "persona_switch",
    })

    def __init__(
        self,
        memory_store: AbstractMemoryStore,
        intent_graph: IntentGraph | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._navigator: IntentNavigator | None = None
        if intent_graph is not None:
            self._navigator = IntentNavigator(intent_graph)

    def retrieve(self, query: str, branch_id: str, intent: Optional[str] = None) -> RetrievedContext:
        """Retrieve relevant memories with optional intent graph navigation."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        effective_intent = intent
        if effective_intent is not None and effective_intent not in self._VALID_INTENTS:
            effective_intent = "retrieve"

        # L2 vector retrieval
        ctx = self._memory_store.retrieve(query, branch_id, intent=effective_intent or "retrieve")

        # L3 intent graph boost (MVA simplified hybrid fusion)
        if self._navigator is not None and effective_intent is not None and effective_intent != "retrieve":
            concept_scores = self._navigator.navigate(query, effective_intent, branch_id)
            if concept_scores:
                ctx = replace(
                    ctx,
                    navigation_path=[{"concept_id": c, "score": s} for c, s in concept_scores],
                )

        return ctx
