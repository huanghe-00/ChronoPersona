"""Intent navigator for hybrid retrieval (graph + vector)."""

from __future__ import annotations

from typing import Dict, List, Tuple

from chronopersona.contracts.schemas.semantic import IntentPattern
from chronopersona.memory_system.l3_semantic.intent_graph import IntentGraph


class IntentNavigator:
    """Simplified 6-step intent graph navigation for MVA."""

    def __init__(
        self,
        graph: IntentGraph,
        patterns: List[IntentPattern] | None = None,
    ) -> None:
        self._graph = graph
        self._patterns: Dict[str, IntentPattern] = {}
        if patterns:
            for p in patterns:
                self._patterns[p.intent_type] = p

    def register_pattern(self, pattern: IntentPattern) -> None:
        self._patterns[pattern.intent_type] = pattern

    def navigate(
        self,
        query: str,
        intent_type: str,
        branch_id: str,
    ) -> List[Tuple[str, float]]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        pattern = self._patterns.get(intent_type)
        if pattern is None:
            return []
        concepts = self._graph.get_concepts(branch_id)
        entry_nodes: List[str] = []
        for concept in concepts:
            if concept.name in query:
                entry_nodes.append(concept.id)
        if not entry_nodes:
            return []
        results: Dict[str, float] = {}
        for node_id in entry_nodes:
            nav = self._graph.navigate(
                start_node_id=node_id,
                entry_edge_types=pattern.entry_edge_types,
                max_hops=pattern.max_hops,
                branch_id=branch_id,
            )
            for target_id, _hop, weight in nav:
                results[target_id] = max(results.get(target_id, 0.0), weight)
        return sorted(results.items(), key=lambda x: x[1], reverse=True)
