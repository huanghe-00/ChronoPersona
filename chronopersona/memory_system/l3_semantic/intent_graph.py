"""In-memory intent graph for L3 semantic navigation."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Set, Tuple

from chronopersona.contracts.schemas.semantic import Concept, SemanticEdge


class IntentGraph:
    """Memory-based intent graph with branch isolation."""

    def __init__(self) -> None:
        self._concepts: Dict[str, Dict[str, Concept]] = {}
        self._memory_nodes: Dict[str, Dict[str, str]] = {}
        self._edges: Dict[str, List[SemanticEdge]] = {}

    def add_concept(self, concept: Concept) -> None:
        if not concept.branch_id:
            raise ValueError("branch_id must not be empty")
        self._concepts.setdefault(concept.branch_id, {})[concept.id] = concept

    def add_memory_node(self, memory_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._memory_nodes.setdefault(branch_id, {})[memory_id] = memory_id

    def add_edge(self, edge: SemanticEdge) -> None:
        if not edge.branch_id:
            raise ValueError("branch_id must not be empty")
        if edge.edge_type not in {
            "IS_A", "MENTIONS", "TEMPORAL_NEXT", "CAUSED",
            "CONTRADICTS", "BELONGS_TO", "SIMILAR_TO", "TRIGGERED_BY",
        }:
            raise ValueError(f"unsupported edge_type: {edge.edge_type}")
        self._edges.setdefault(edge.branch_id, []).append(edge)

    def navigate(
        self,
        start_node_id: str,
        entry_edge_types: list[str],
        max_hops: int = 3,
        branch_id: str = "main",
    ) -> list[Tuple[str, int, float]]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        edges = self._edges.get(branch_id, [])
        visited: Set[str] = {start_node_id}
        queue: deque[Tuple[str, int, float]] = deque([(start_node_id, 0, 1.0)])
        results: List[Tuple[str, int, float]] = []

        while queue:
            node_id, hop, weight = queue.popleft()
            if hop >= max_hops:
                continue
            for edge in edges:
                if edge.source_id != node_id:
                    continue
                if edge.edge_type not in entry_edge_types:
                    continue
                target = edge.target_id
                if target in visited:
                    continue
                visited.add(target)
                new_weight = weight * edge.weight * 0.9
                results.append((target, hop + 1, new_weight))
                queue.append((target, hop + 1, new_weight))

        results.sort(key=lambda x: x[2], reverse=True)
        return results

    def get_concepts(self, branch_id: str) -> list[Concept]:
        return list(self._concepts.get(branch_id, {}).values())

    def get_edges(self, branch_id: str, edge_type: str | None = None) -> list[SemanticEdge]:
        edges = self._edges.get(branch_id, [])
        if edge_type is None:
            return edges
        return [e for e in edges if e.edge_type == edge_type]
