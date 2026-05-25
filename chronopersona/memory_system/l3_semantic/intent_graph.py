"""In-memory intent graph for L3 semantic navigation."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Set, Tuple

from chronopersona.contracts.schemas.semantic import Concept, SemanticEdge


class IntentGraph:
    """Memory-based intent graph with branch isolation."""

    def __init__(self) -> None:
        self._concepts: Dict[str, Dict[str, Concept]] = {}
        self._memory_nodes: Dict[str, Dict[str, str]] = {}
        self._edges: Dict[str, List[SemanticEdge]] = {}
        self._deprecated_edges: Dict[str, Set[str]] = {}  # branch_id -> set(edge_id)

    def add_concept(self, concept: Concept, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if concept.branch_id != branch_id:
            raise ValueError("concept.branch_id does not match provided branch_id")
        self._concepts.setdefault(concept.branch_id, {})[concept.id] = concept

    def add_memory_node(self, memory_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._memory_nodes.setdefault(branch_id, {})[memory_id] = memory_id

    def add_edge(self, edge: SemanticEdge, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if edge.branch_id != branch_id:
            raise ValueError("edge.branch_id does not match provided branch_id")
        if edge.edge_type not in {
            "IS_A", "MENTIONS", "TEMPORAL_NEXT", "CAUSED",
            "CONTRADICTS", "BELONGS_TO", "SIMILAR_TO", "TRIGGERED_BY",
        }:
            raise ValueError(f"unsupported edge_type: {edge.edge_type}")
        self._edges.setdefault(edge.branch_id, []).append(edge)
        # Sync _deprecated_edges if edge is added with non-active status
        if edge.status != "active":
            self._deprecated_edges.setdefault(branch_id, set()).add(edge.id)

    def navigate(
        self,
        start_node_id: str,
        entry_edge_types: List[str],
        branch_id: str,
        max_hops: int = 3,
    ) -> List[Tuple[str, int, float]]:
        """BFS navigation from start node along specified edge types.

        Supports bidirectional traversal for causal and associative edges.
        Only edges with status == "active" are traversed.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        edges = self._edges.get(branch_id, [])
        deprecated = self._deprecated_edges.get(branch_id, set())
        # Filter out deprecated/archived edges using _deprecated_edges as source of truth
        active_edges = [e for e in edges if e.id not in deprecated]
        visited: Set[str] = {start_node_id}
        queue: Deque[Tuple[str, int, float]] = deque([(start_node_id, 0, 1.0)])
        results: List[Tuple[str, int, float]] = []

        while queue:
            node_id, hop, weight = queue.popleft()
            if hop >= max_hops:
                continue

            for edge in active_edges:
                candidates: List[str] = []
                if edge.source_id == node_id and edge.edge_type in entry_edge_types:
                    candidates.append(edge.target_id)
                if edge.target_id == node_id and edge.edge_type in entry_edge_types:
                    candidates.append(edge.source_id)

                for target in candidates:
                    if target in visited:
                        continue
                    visited.add(target)
                    new_weight = weight * edge.weight * 0.9
                    results.append((target, hop + 1, new_weight))
                    queue.append((target, hop + 1, new_weight))

        results.sort(key=lambda x: x[2], reverse=True)
        return results

    def deprecate_edge(self, edge_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._deprecated_edges.setdefault(branch_id, set()).add(edge_id)
        # Also update the edge's status field for navigate filtering
        for edge in self._edges.get(branch_id, []):
            if edge.id == edge_id:
                edge.status = "deprecated"
                break

    def reactivate_edge(self, edge_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._deprecated_edges.setdefault(branch_id, set()).discard(edge_id)
        # Restore edge status to active
        for edge in self._edges.get(branch_id, []):
            if edge.id == edge_id:
                edge.status = "active"
                break

    def get_concepts(self, branch_id: str) -> List[Concept]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return list(self._concepts.get(branch_id, {}).values())

    def get_edges(self, branch_id: str, edge_type: Optional[str] = None) -> List[SemanticEdge]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        edges = self._edges.get(branch_id, [])
        deprecated = self._deprecated_edges.get(branch_id, set())
        edges = [e for e in edges if e.id not in deprecated]
        if edge_type is None:
            return edges
        return [e for e in edges if e.edge_type == edge_type]
