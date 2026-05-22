"""Unit tests for L3 Unlearning (deprecated edges)."""

import pytest

from chronopersona.contracts.schemas.semantic import Concept, SemanticEdge
from chronopersona.memory_system.l3_semantic.intent_graph import IntentGraph


class TestL3Unlearning:
    """Tests for semantic edge deprecation and reactivation."""

    def test_deprecate_edge_hides_from_get_edges(self) -> None:
        """T01: deprecated edge is excluded from get_edges."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        graph.add_edge(
            SemanticEdge(
                id="e1", source_id="c1", target_id="c2",
                edge_type="MENTIONS", branch_id="main",
            ), branch_id="main"
        )
        assert len(graph.get_edges("main")) == 1
        graph.deprecate_edge("e1", "main")
        assert len(graph.get_edges("main")) == 0

    def test_reactivate_edge_restores_visibility(self) -> None:
        """T02: reactivated edge reappears in get_edges."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        graph.add_edge(
            SemanticEdge(
                id="e1", source_id="c1", target_id="c2",
                edge_type="MENTIONS", branch_id="main",
            ), branch_id="main"
        )
        graph.deprecate_edge("e1", "main")
        graph.reactivate_edge("e1", "main")
        assert len(graph.get_edges("main")) == 1

    def test_deprecate_empty_branch_raises_valueerror(self) -> None:
        """T03: deprecate_edge with empty branch_id raises ValueError."""
        graph = IntentGraph()
        with pytest.raises(ValueError):
            graph.deprecate_edge("e1", "")

    def test_reactivate_empty_branch_raises_valueerror(self) -> None:
        """T04: reactivate_edge with empty branch_id raises ValueError."""
        graph = IntentGraph()
        with pytest.raises(ValueError):
            graph.reactivate_edge("e1", "")

    def test_branch_isolation_for_deprecated(self) -> None:
        """T05: deprecation in one branch does not affect another."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="a"), branch_id="a")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="a"), branch_id="a")
        graph.add_edge(
            SemanticEdge(
                id="e1", source_id="c1", target_id="c2",
                edge_type="MENTIONS", branch_id="a",
            ), branch_id="a"
        )
        graph.deprecate_edge("e1", "a")
        assert len(graph.get_edges("b")) == 0
        assert len(graph.get_edges("a")) == 0
