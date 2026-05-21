"""Hybrid retriever: fuses L2 vector, L3 graph, and keyword recall."""

from typing import Any

from loguru import logger

from chronopersona.contracts.interfaces import IHybridRetriever
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext


class HybridRetriever(IHybridRetriever):
    """MVA hybrid fusion: interleave L2 episodic + L3 graph results."""

    def __init__(
        self,
        episodic_store: Any,
        intent_navigator: Any,
    ) -> None:
        self._episodic = episodic_store
        self._navigator = intent_navigator

    def retrieve(
        self,
        query: str,
        branch_id: str,
        intent: str | None = None,
        top_k: int = 5,
    ) -> RetrievedContext:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        # L2 Vector recall
        l2_ctx = self._episodic.retrieve(query, branch_id, top_k=top_k)
        l2_memories = list(l2_ctx.episodic_memories)

        # L3 Graph recall (optional, only if intent provided)
        l3_memories: list[MemoryEntry] = []
        if intent and self._navigator:
            try:
                nav_results = self._navigator.navigate(
                    query, intent, branch_id
                )
                # Convert navigation results to MemoryEntry stubs
                for target_id, hop, weight in nav_results[:top_k]:
                    l3_memories.append(
                        MemoryEntry(
                            id=f"nav_{target_id}",
                            content=f"[Graph] {target_id} (hop={hop}, w={weight:.2f})",
                            metadata={"source": "intent_graph", "hop": hop},
                        )
                    )
            except Exception:
                logger.warning("Graph navigation failed for intent={}", intent)

        # Fusion: interleave L2 + L3, deduplicate by id
        seen: set[str] = set()
        fused: list[MemoryEntry] = []
        l2_idx, l3_idx = 0, 0

        while len(fused) < top_k and (l2_idx < len(l2_memories) or l3_idx < len(l3_memories)):
            if l2_idx < len(l2_memories):
                m = l2_memories[l2_idx]
                l2_idx += 1
                if m.id not in seen:
                    seen.add(m.id)
                    fused.append(m)
            if l3_idx < len(l3_memories) and len(fused) < top_k:
                m = l3_memories[l3_idx]
                l3_idx += 1
                if m.id not in seen:
                    seen.add(m.id)
                    fused.append(m)

        logger.info(
            "HybridRetriever: query='{}' branch='{}' intent='{}' => {} results (L2={}, L3={})",
            query, branch_id, intent, len(fused), len(l2_memories), len(l3_memories)
        )

        return RetrievedContext(
            working_memories=list(l2_ctx.working_memories),
            episodic_memories=fused,
            semantic_facts=list(l2_ctx.semantic_facts),
            insights=list(l2_ctx.insights),
            navigation_path=[{"target": m.id, "source": m.metadata.get("source", "vector")} for m in fused],
            total_tokens=sum(len(m.content) for m in fused),
        )
