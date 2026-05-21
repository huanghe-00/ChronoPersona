"""Tests for MVO seed loader."""

import pytest

from chronopersona.memory_system.l3_semantic.intent_graph import IntentGraph
from chronopersona.memory_system.l3_semantic.mvo_seed_loader import MVOSeedLoader


class TestMVOSeedLoader:
    """Tests for MVO seed loading."""

    def test_load_populates_concepts(self) -> None:
        """Loading seeds populates default concepts."""
        graph = IntentGraph()
        loader = MVOSeedLoader(graph)
        loader.load("main", "main")
        concepts = graph.get_concepts("main")
        assert len(concepts) > 0
        assert any(c.id == "c_food" for c in concepts)

    def test_load_is_idempotent(self) -> None:
        """Repeated loading does not duplicate concepts."""
        graph = IntentGraph()
        loader = MVOSeedLoader(graph)
        loader.load("main", "main")
        first_count = len(graph.get_concepts("main"))
        loader.load("main")
        second_count = len(graph.get_concepts("main"))
        assert first_count == second_count

    def test_load_branch_isolation(self) -> None:
        """Seeds are loaded into specified branch only."""
        graph = IntentGraph()
        loader = MVOSeedLoader(graph)
        loader.load("default", "b1")
        assert len(graph.get_concepts("b1")) > 0
        assert len(graph.get_concepts("b2")) == 0
