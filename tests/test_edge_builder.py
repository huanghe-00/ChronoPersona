"""Unit tests for SimpleEdgeBuilder."""

import pytest

from chronopersona.contracts.interfaces import IEdgeBuilder
from chronopersona.contracts.schemas.semantic import SemanticEdge
from chronopersona.memory_system.l3_semantic.edge_builder import SimpleEdgeBuilder
from chronopersona.mocks.mock_edge_builder import MockEdgeBuilder


class TestSimpleEdgeBuilder:
    """Tests for Tier 1 rule-based edge builder."""

    def test_build_mentions_from_entities(self) -> None:
        """T01: Every entity gets a MENTIONS edge."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        edges = builder.build_edges(
            turn_id="t1",
            session_id="s1",
            branch_id="main",
            content="I like pizza",
            entities=["pizza", "food"],
        )
        mention_edges = [e for e in edges if e.edge_type == "MENTIONS"]
        assert len(mention_edges) == 2
        assert any(e.target_id == "pizza" for e in mention_edges)

    def test_build_temporal_next_with_prev_turn(self) -> None:
        """T02: prev_turn_id creates TEMPORAL_NEXT edge."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        edges = builder.build_edges(
            turn_id="t2",
            session_id="s1",
            branch_id="main",
            content="ok",
            entities=[],
            prev_turn_id="t1",
        )
        temporal = [e for e in edges if e.edge_type == "TEMPORAL_NEXT"]
        assert len(temporal) == 1
        assert temporal[0].source_id == "t1"
        assert temporal[0].target_id == "t2"

    def test_no_temporal_next_without_prev(self) -> None:
        """T03: No prev_turn_id means no TEMPORAL_NEXT edge."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        edges = builder.build_edges(
            turn_id="t1",
            session_id="s1",
            branch_id="main",
            content="start",
            entities=[],
        )
        assert not any(e.edge_type == "TEMPORAL_NEXT" for e in edges)

    def test_build_caused_from_template(self) -> None:
        """T04: Chinese causal template produces CAUSED edge."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        edges = builder.build_edges(
            turn_id="t1",
            session_id="s1",
            branch_id="main",
            content="因为压力大，所以失眠了",
            entities=[],
        )
        caused = [e for e in edges if e.edge_type == "CAUSED"]
        assert len(caused) >= 1
        assert caused[0].weight == 0.85

    def test_build_contradicts_from_antonyms(self) -> None:
        """T05: Antonym pairs in content produce CONTRADICTS edge."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        edges = builder.build_edges(
            turn_id="t1",
            session_id="s1",
            branch_id="main",
            content="我喜欢川菜但讨厌辣味",
            entities=[],
        )
        contradicts = [e for e in edges if e.edge_type == "CONTRADICTS"]
        assert len(contradicts) >= 1

    def test_empty_branch_raises_valueerror(self) -> None:
        """T06: Empty branch_id raises ValueError."""
        builder: IEdgeBuilder = SimpleEdgeBuilder()
        with pytest.raises(ValueError):
            builder.build_edges("t1", "s1", "", "x", [])

    def test_supported_types(self) -> None:
        """T07: Returns expected Tier 1 types."""
        builder = SimpleEdgeBuilder()
        assert "MENTIONS" in builder.supported_types()
        assert "CAUSED" in builder.supported_types()


class TestMockEdgeBuilder:
    """Tests for MockEdgeBuilder."""

    def test_mock_is_instance(self) -> None:
        """T08: Mock is valid IEdgeBuilder."""
        builder: IEdgeBuilder = MockEdgeBuilder()
        assert isinstance(builder, IEdgeBuilder)

    def test_mock_returns_fixed_edge(self) -> None:
        """T09: Mock returns predictable MENTIONS edge."""
        builder = MockEdgeBuilder()
        edges = builder.build_edges("t1", "s1", "main", "hi", ["e1"])
        assert len(edges) == 1
        assert edges[0].edge_type == "MENTIONS"
