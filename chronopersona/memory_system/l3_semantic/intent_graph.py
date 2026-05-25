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

    def navigate(
        self,
        start_node_id: str,
        entry_edge_types: List[str],
        branch_id: str,
        max_hops: int = 3,
    ) -> List[Tuple[str, int, float]]:
        """BFS navigation from start node along specified edge types.

        Supports bidirectional traversal for causal and associative edges.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        edges = self._edges.get(branch_id, [])
        visited: Set[str] = {start_node_id}
        queue: Deque[Tuple[str, int, float]] = deque([(start_node_id, 0, 1.0)])
        results: List[Tuple[str, int, float]] = []

        while queue:
            node_id, hop, weight = queue.popleft()
            if hop >= max_hops:
                continue

            for edge in edges:
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

    def reactivate_edge(self, edge_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._deprecated_edges.setdefault(branch_id, set()).discard(edge_id)

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
"""Intent graph implementation for L3 semantic memory."""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from chronopersona.contracts.schemas.semantic import Concept, IntentPattern, SemanticEdge


class IntentGraph:
    """In-memory intent graph with typed edges and navigation support."""

    def __init__(self) -> None:
        self._concepts: Dict[str, Concept] = {}
        self._edges: Dict[str, SemanticEdge] = {}
        # adjacency: source_id -> list of edge ids
        self._adjacency: Dict[str, List[str]] = {}

    def add_concept(self, concept: Concept) -> None:
        """Add a concept node to the graph."""
        self._concepts[concept.id] = concept
        logger.info("Added concept '{}' (type={})", concept.name, concept.concept_type)

    def add_edge(self, edge: SemanticEdge) -> None:
        """Add a typed edge between two concepts."""
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.id)
        logger.info(
            "Added edge '{}' ({} -> {}) type={}",
            edge.id,
            edge.source_id,
            edge.target_id,
            edge.edge_type,
        )

    def get_edges(
        self,
        source_id: Optional[str] = None,
        edge_type: Optional[str] = None,
        branch_id: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[SemanticEdge]:
        """Retrieve edges with optional filters.

        Args:
            source_id: If provided, only edges originating from this concept.
            edge_type: If provided, only edges of this type.
            branch_id: If provided, only edges belonging to this branch.
            include_deprecated: If False (default), edges with status='deprecated' are excluded.

        Returns:
            Filtered list of SemanticEdge objects.
        """
        result: List[SemanticEdge] = []
        for edge in self._edges.values():
            if source_id is not None and edge.source_id != source_id:
                continue
            if edge_type is not None and edge.edge_type != edge_type:
                continue
            if branch_id is not None and edge.branch_id != branch_id:
                continue
            if not include_deprecated and getattr(edge, "status", "active") == "deprecated":
                continue
            result.append(edge)
        return result

    def navigate(
        self,
        start_id: str,
        pattern: IntentPattern,
        branch_id: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Concept]:
        """Navigate the graph following an intent pattern.

        Args:
            start_id: Starting concept id.
            pattern: IntentPattern describing allowed edge types and max hops.
            branch_id: Optional branch filter.
            include_deprecated: If False, deprecated edges are skipped.

        Returns:
            List of reached Concept nodes (excluding the start node).
        """
        visited: set[str] = {start_id}
        frontier: List[str] = [start_id]
        reached: List[Concept] = []

        for _ in range(pattern.max_hops):
            next_frontier: List[str] = []
            for node_id in frontier:
                edges = self.get_edges(
                    source_id=node_id,
                    branch_id=branch_id,
                    include_deprecated=include_deprecated,
                )
                for edge in edges:
                    if edge.edge_type not in pattern.entry_edge_types:
                        continue
                    target = edge.target_id
                    if target in visited:
                        continue
                    visited.add(target)
                    next_frontier.append(target)
                    concept = self._concepts.get(target)
                    if concept is not None:
                        reached.append(concept)
            frontier = next_frontier
            if not frontier:
                break

        return reached

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Return a concept by id, or None if not found."""
        return self._concepts.get(concept_id)
