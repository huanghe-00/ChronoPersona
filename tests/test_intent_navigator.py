"""Tests for IntentNavigator."""

import pytest

from chronopersona.contracts.schemas.semantic import Concept, IntentPattern, SemanticEdge
from chronopersona.memory_system.l3_semantic import IntentGraph, IntentNavigator


class TestIntentNavigator:
    """Tests for intent-driven graph navigation."""

    def test_navigate_finds_reachable_nodes(self) -> None:
        """Navigation from a concept finds reachable memory nodes."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_food", "食物", "abstract", branch_id="main"))
        graph.add_concept(Concept("c_sichuan", "川菜", "food", parent_id="c_food", branch_id="main"))
        graph.add_memory_node("mem-1", "main")
        graph.add_edge(SemanticEdge(
            id="e1",
            source_id="c_sichuan",
            target_id="mem-1",
            edge_type="MENTIONS",
            branch_id="main",
        ))

        pattern = IntentPattern(
            intent_type="test_intent",
            trigger_keywords=["川菜"],
            entry_edge_types=["MENTIONS"],
            max_hops=2,
        )
        nav = IntentNavigator(graph, [pattern])

        results = nav.navigate("我喜欢川菜", "test_intent", "main")
        assert len(results) == 1
        assert results[0][0] == "mem-1"
        assert results[0][1] > 0.0

    def test_navigate_unknown_intent_returns_empty(self) -> None:
        """Unknown intent type returns empty list."""
        graph = IntentGraph()
        nav = IntentNavigator(graph)
        assert nav.navigate("test", "unknown", "main") == []

    def test_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        graph = IntentGraph()
        nav = IntentNavigator(graph)
        with pytest.raises(ValueError):
            nav.navigate("test", "empathize", "")

    def test_navigate_no_entry_nodes_returns_empty(self) -> None:
        """Query matching no concepts returns empty results."""
        graph = IntentGraph()
        graph.add_concept(Concept("c_food", "食物", "abstract", branch_id="main"))
        pattern = IntentPattern("test", ["不匹配"], ["IS_A"], 2)
        nav = IntentNavigator(graph, [pattern])
        assert nav.navigate("random query", "test", "main") == []
