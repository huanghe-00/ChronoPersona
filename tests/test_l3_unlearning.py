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

    def test_add_edge_with_deprecated_status_syncs_to_filter(self) -> None:
        """T07: Adding edge with status='deprecated' directly is filtered by get_edges and navigate."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        # Add edge directly with deprecated status
        graph.add_edge(
            SemanticEdge(
                id="e1", source_id="c1", target_id="c2",
                edge_type="MENTIONS", branch_id="main", status="deprecated",
            ), branch_id="main"
        )
        # get_edges should filter it
        assert len(graph.get_edges("main")) == 0
        # navigate should also filter it
        from chronopersona.contracts.schemas.semantic import IntentPattern
        from chronopersona.memory_system.l3_semantic import IntentNavigator
        pattern = IntentPattern("retrieve", ["A"], ["MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])
        results = nav.navigate("A", "retrieve", "main")
        assert len(results) == 0

    def test_get_edges_filters_by_edge_type(self) -> None:
        """T06: get_edges with edge_type filters correctly and excludes deprecated."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        graph.add_edge(
            SemanticEdge("e1", "c1", "c2", "MENTIONS", branch_id="main"),
            branch_id="main",
        )
        graph.add_edge(
            SemanticEdge("e2", "c1", "c2", "CAUSED", branch_id="main"),
            branch_id="main",
        )
        # Filter by type
        mentions = graph.get_edges("main", edge_type="MENTIONS")
        assert len(mentions) == 1
        assert mentions[0].edge_type == "MENTIONS"
        # Deprecate one, filter by type should return empty
        graph.deprecate_edge("e1", "main")
        mentions_after = graph.get_edges("main", edge_type="MENTIONS")
        assert len(mentions_after) == 0
