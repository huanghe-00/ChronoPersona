"""Unit tests for HybridRetriever."""

from unittest.mock import MagicMock

import pytest

from chronopersona.contracts.interfaces import IHybridRetriever
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.retrieval.hybrid_retriever import HybridRetriever
from chronopersona.mocks.mock_hybrid_retriever import MockHybridRetriever


class TestHybridRetriever:
    """Tests for real HybridRetriever fusion logic."""

    def test_vector_only_when_no_intent(self) -> None:
        """T01: Without intent, only L2 vector results returned."""
        episodic = MagicMock()
        episodic.retrieve.return_value = RetrievedContext(
            episodic_memories=[MemoryEntry(id="m1", content="vector result")],
            total_tokens=10,
        )
        retriever: IHybridRetriever = HybridRetriever(episodic, None)
        ctx = retriever.retrieve("test", "main", intent=None)
        assert len(ctx.episodic_memories) == 1
        assert ctx.episodic_memories[0].id == "m1"

    def test_vector_plus_graph_fusion(self) -> None:
        """T02: With intent, L2 and L3 results are interleaved."""
        episodic = MagicMock()
        episodic.retrieve.return_value = RetrievedContext(
            episodic_memories=[MemoryEntry(id="m1", content="L2")],
            total_tokens=5,
        )
        navigator = MagicMock()
        navigator.navigate.return_value = [("c2", 1, 0.9)]

        retriever: IHybridRetriever = HybridRetriever(episodic, navigator)
        ctx = retriever.retrieve("test", "main", intent="retrieve", top_k=2)

        ids = [m.id for m in ctx.episodic_memories]
        assert "m1" in ids
        assert any("nav_c2" in i for i in ids)

    def test_empty_branch_raises_valueerror(self) -> None:
        """T03: Empty branch_id raises ValueError."""
        retriever: IHybridRetriever = HybridRetriever(MagicMock(), None)
        with pytest.raises(ValueError):
            retriever.retrieve("test", "", intent=None)

    def test_deduplication(self) -> None:
        """T04: Duplicate ids across L2/L3 are deduplicated."""
        episodic = MagicMock()
        episodic.retrieve.return_value = RetrievedContext(
            episodic_memories=[MemoryEntry(id="dup", content="L2")],
            total_tokens=5,
        )
        navigator = MagicMock()
        navigator.navigate.return_value = [("dup", 1, 0.8)]

        retriever: IHybridRetriever = HybridRetriever(episodic, navigator)
        ctx = retriever.retrieve("test", "main", intent="retrieve", top_k=2)
        assert len(ctx.episodic_memories) == 1


class TestMockHybridRetriever:
    """Tests for MockHybridRetriever."""

    def test_mock_is_instance(self) -> None:
        """T05: Mock is valid IHybridRetriever."""
        retriever: IHybridRetriever = MockHybridRetriever()
        assert isinstance(retriever, IHybridRetriever)

    def test_mock_returns_context(self) -> None:
        """T06: Mock returns predictable context."""
        retriever = MockHybridRetriever()
        ctx = retriever.retrieve("q", "main")
        assert len(ctx.episodic_memories) == 1
        assert ctx.episodic_memories[0].id == "mock_hybrid_1"
