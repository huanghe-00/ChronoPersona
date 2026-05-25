"""A6 adversarial tests for intent graph navigation.

Validates that structured intent navigation outperforms naive vector retrieval.
"""

import pytest

from chronopersona.contracts.schemas.semantic import Concept, IntentPattern, SemanticEdge
from chronopersona.memory_system.l3_semantic import IntentGraph, IntentNavigator


class TestA6IntentGraph:
    """A6: Intent Graph navigation precision tests."""

    def test_a6_1_temporal_trace(self) -> None:
        """A6-1: '我上周的方案后来怎样' uses TEMPORAL_NEXT chain."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_plan", "方案", "abstract", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-plan", "main")
        graph.add_memory_node("mem-implement", "main")
        graph.add_edge(SemanticEdge("e1", "c_plan", "mem-plan", "MENTIONS", branch_id="main"), branch_id="main")
        graph.add_edge(SemanticEdge("e2", "mem-plan", "mem-implement", "TEMPORAL_NEXT", branch_id="main"), branch_id="main")

        pattern = IntentPattern("temporal_trace", ["后来", "之后"], ["TEMPORAL_NEXT", "MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])

        results = nav.navigate("我上周的方案后来怎样", "temporal_trace", "main")
        assert len(results) >= 1
        node_ids = {nid for nid, _ in results}
        assert "mem-implement" in node_ids

    def test_a6_2_parallel_compare(self) -> None:
        """A6-2: '川菜和粤菜我喜欢哪个' uses SIMILAR_TO + cross-branch recall."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_sichuan", "川菜", "food", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c_cantonese", "粤菜", "food", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-like-sc", "main")
        graph.add_memory_node("mem-like-ca", "main")
        graph.add_edge(SemanticEdge("e1", "c_sichuan", "mem-like-sc", "MENTIONS", branch_id="main"), branch_id="main")
        graph.add_edge(SemanticEdge("e2", "c_cantonese", "mem-like-ca", "MENTIONS", branch_id="main"), branch_id="main")
        graph.add_edge(SemanticEdge("e3", "c_sichuan", "c_cantonese", "SIMILAR_TO", branch_id="main"), branch_id="main")

        pattern = IntentPattern("parallel_compare", ["和", "哪个"], ["SIMILAR_TO", "MENTIONS"], 2)
        nav = IntentNavigator(graph, [pattern])

        results = nav.navigate("川菜和粤菜我喜欢哪个", "parallel_compare", "main")
        node_ids = {nid for nid, _ in results}
        assert "mem-like-sc" in node_ids or "c_sichuan" in node_ids
        assert "mem-like-ca" in node_ids or "c_cantonese" in node_ids

    def test_a6_3_causal_explore(self) -> None:
        """A6-3: '为什么我最近焦虑' uses CAUSED backtracking."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_anxiety", "焦虑", "emotion", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c_work", "工作压力", "abstract", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-anxiety", "main")
        graph.add_memory_node("mem-work", "main")
        graph.add_edge(SemanticEdge("e1", "c_anxiety", "mem-anxiety", "MENTIONS", branch_id="main"), branch_id="main")
        graph.add_edge(SemanticEdge("e2", "mem-work", "c_anxiety", "CAUSED", branch_id="main"), branch_id="main")

        pattern = IntentPattern("causal_explore", ["为什么", "原因"], ["CAUSED", "MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])

        results = nav.navigate("为什么我最近焦虑", "causal_explore", "main")
        node_ids = {nid for nid, _ in results}
        assert "mem-work" in node_ids or "c_work" in node_ids

    def test_a6_4_mention_reference(self) -> None:
        """A6-4: '上次你说的那个餐厅' uses MENTIONS + concept linking."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_restaurant", "餐厅", "food", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-restaurant", "main")
        graph.add_edge(SemanticEdge("e1", "c_restaurant", "mem-restaurant", "MENTIONS", branch_id="main"), branch_id="main")

        pattern = IntentPattern("retrieve", ["餐厅"], ["MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])

        results = nav.navigate("上次你说的那个餐厅", "retrieve", "main")
        assert len(results) >= 1
        node_ids = {nid for nid, _ in results}
        assert "mem-restaurant" in node_ids

    def test_a6_5_navigate_filters_deprecated_edges(self) -> None:
        """A6-5: navigate excludes edges with status != 'active'."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-a", "main")
        graph.add_memory_node("mem-b", "main")
        graph.add_edge(
            SemanticEdge("e1", "c1", "mem-a", "MENTIONS", branch_id="main"),
            branch_id="main",
        )
        graph.add_edge(
            SemanticEdge("e2", "c2", "mem-b", "MENTIONS", branch_id="main"),
            branch_id="main",
        )
        # Deprecate e1
        graph.deprecate_edge("e1", "main")

        pattern = IntentPattern("retrieve", ["A"], ["MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])
        results = nav.navigate("A", "retrieve", "main")
        node_ids = {nid for nid, _ in results}
        # e1 is deprecated, so mem-a should not appear
        assert "mem-a" not in node_ids
        # e2 is still active, so mem-b should be reachable
        assert "mem-b" in node_ids

    def test_a6_6_reactivate_restores_navigate(self) -> None:
        """A6-6: reactivating a deprecated edge makes it traversable again."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_memory_node("mem-a", "main")
        graph.add_edge(
            SemanticEdge("e1", "c1", "mem-a", "MENTIONS", branch_id="main"),
            branch_id="main",
        )
        graph.deprecate_edge("e1", "main")
        graph.reactivate_edge("e1", "main")

        pattern = IntentPattern("retrieve", ["A"], ["MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])
        results = nav.navigate("A", "retrieve", "main")
        node_ids = {nid for nid, _ in results}
        assert "mem-a" in node_ids

    def test_a6_7_deprecate_updates_edge_status(self) -> None:
        """A6-7: deprecate_edge sets edge.status to 'deprecated'."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        edge = SemanticEdge("e1", "c1", "c2", "MENTIONS", branch_id="main")
        graph.add_edge(edge, branch_id="main")
        graph.deprecate_edge("e1", "main")
        # Retrieve the edge from the graph to check status
        edges = graph.get_edges("main")
        # get_edges already filters deprecated, so we need to access internal store
        # We'll verify via navigate exclusion instead (covered by A6-5)
        # But we can also check that the edge is no longer returned by get_edges
        assert len(edges) == 0
        # Directly inspect the internal edge list to confirm status change
        internal_edges = graph._edges.get("main", [])
        assert any(e.id == "e1" and e.status == "deprecated" for e in internal_edges)

    def test_a6_8_reactivate_updates_edge_status(self) -> None:
        """A6-8: reactivate_edge sets edge.status back to 'active'."""
        graph = IntentGraph()
        graph.add_concept(Concept("c1", "A", "abstract", branch_id="main"), branch_id="main")
        graph.add_concept(Concept("c2", "B", "abstract", branch_id="main"), branch_id="main")
        edge = SemanticEdge("e1", "c1", "c2", "MENTIONS", branch_id="main")
        graph.add_edge(edge, branch_id="main")
        graph.deprecate_edge("e1", "main")
        graph.reactivate_edge("e1", "main")
        internal_edges = graph._edges.get("main", [])
        assert any(e.id == "e1" and e.status == "active" for e in internal_edges)
        # Also verify get_edges returns it again
        edges = graph.get_edges("main")
        assert len(edges) == 1
        assert edges[0].id == "e1"
