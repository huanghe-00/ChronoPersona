"""Unit tests for FaissEpisodicStore production implementation."""

from typing import List

import pytest

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic import FaissEpisodicStore, MockBGEEmbedder


class TestFaissEpisodicStore:
    """Tests for FAISS-backed episodic store."""

    def test_add_and_retrieve_vector_search(self) -> None:
        """T01: Vector similarity search returns relevant memories."""
        embedder = MockBGEEmbedder()
        store = FaissEpisodicStore(embedder=embedder)
        store.add(MemoryEntry(content="I love Sichuan cuisine"), branch_id="main")
        store.add(MemoryEntry(content="The weather is nice today"), branch_id="main")

        ctx = store.retrieve("Sichuan food", branch_id="main", top_k=2)
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("Sichuan" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """T02: Memories do not leak across branches."""
        embedder = MockBGEEmbedder()
        store = FaissEpisodicStore(embedder=embedder)
        store.add(MemoryEntry(content="secret branch content"), branch_id="b1")

        ctx = store.retrieve("secret", branch_id="b2", top_k=5)
        assert len(ctx.episodic_memories) == 0

    def test_delete_removes_from_index(self) -> None:
        """T03: Deleted memory is no longer retrievable."""
        embedder = MockBGEEmbedder()
        store = FaissEpisodicStore(embedder=embedder)
        mid = store.add(MemoryEntry(content="temporary data"), branch_id="main")
        assert store.delete(mid, branch_id="main") is True

        ctx = store.retrieve("temporary data", branch_id="main", top_k=5)
        assert len(ctx.episodic_memories) == 0

    def test_empty_branch_retrieve(self) -> None:
        """T04: Retrieve from empty branch returns empty context."""
        embedder = MockBGEEmbedder()
        store = FaissEpisodicStore(embedder=embedder)
        ctx = store.retrieve("anything", branch_id="empty", top_k=5)
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 0
        assert ctx.total_tokens == 0

    def test_add_empty_branch_raises_valueerror(self) -> None:
        """T05: Adding with empty branch_id raises ValueError."""
        embedder = MockBGEEmbedder()
        store = FaissEpisodicStore(embedder=embedder)
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")
