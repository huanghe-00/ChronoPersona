"""Tests for L3 IntentGraph."""

import pytest

from chronopersona.contracts.schemas.semantic import Concept, SemanticEdge
from chronopersona.memory_system.l3_semantic import IntentGraph


class TestIntentGraph:
    """Tests for IntentGraph memory implementation."""

    def test_add_concept_branch_isolation(self) -> None:
        """Concepts are isolated by branch_id."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "概念1", "abstract", branch_id="b1"))
        assert len(graph.get_concepts("b1")) == 1
        assert len(graph.get_concepts("b2")) == 0

    def test_add_edge_validates_type(self) -> None:
        """Only 8 edge types are allowed."""
        graph = IntentGraph()
        with pytest.raises(ValueError):
            graph.add_edge(SemanticEdge("e1", "a", "b", "INVALID", branch_id="main"))

    def test_navigate_respects_max_hops(self) -> None:
        """BFS navigation respects max_hops limit."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "起点", "abstract", branch_id="main"))
        graph.add_concept(Concept("c2", "中间", "abstract", branch_id="main"))
        graph.add_concept(Concept("c3", "终点", "abstract", branch_id="main"))
        graph.add_edge(SemanticEdge("e1", "c1", "c2", "IS_A", branch_id="main"))
        graph.add_edge(SemanticEdge("e2", "c2", "c3", "IS_A", branch_id="main"))

        results = graph.navigate("c1", ["IS_A"], max_hops=1, branch_id="main")
        assert len(results) == 1
        assert results[0][0] == "c2"

        results = graph.navigate("c1", ["IS_A"], max_hops=2, branch_id="main")
        assert len(results) == 2

    def test_navigate_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        graph = IntentGraph()
        with pytest.raises(ValueError):
            graph.navigate("c1", ["IS_A"], branch_id="")

    def test_navigate_no_matching_edges_returns_empty(self) -> None:
        """No matching edges returns empty list."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "起点", "abstract", branch_id="main"))
        assert graph.navigate("c1", ["MENTIONS"], branch_id="main") == []
