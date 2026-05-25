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
"""Unit tests for FaissEpisodicStore (Week 2 Day 3)."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.faiss_store import FaissEpisodicStore


class TestFaissEpisodicStore:
    """T01-T08: FaissEpisodicStore tests."""

    def test_add_and_retrieve_basic(self) -> None:
        """T01: Add and retrieve a memory entry."""
        store = FaissEpisodicStore()
        entry = MemoryEntry(content="I like Sichuan food")
        mid = store.add(entry, branch_id="main")
        assert mid.startswith("faiss-")

        ctx = store.retrieve("Sichuan", branch_id="main")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("Sichuan" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """T02: Different branches have isolated memories."""
        store = FaissEpisodicStore()
        store.add(MemoryEntry(content="secret"), branch_id="therapist")
        ctx = store.retrieve("secret", branch_id="rpg-hero")
        assert len(ctx.episodic_memories) == 0

    def test_retrieve_top_k_limit(self) -> None:
        """T03: Retrieve respects top_k limit."""
        store = FaissEpisodicStore()
        for i in range(10):
            store.add(MemoryEntry(content=f"memory {i}"), branch_id="main")
        ctx = store.retrieve("memory", branch_id="main", top_k=3)
        assert len(ctx.episodic_memories) <= 3

    def test_delete_memory(self) -> None:
        """T04: Delete removes a memory entry."""
        store = FaissEpisodicStore()
        mid = store.add(MemoryEntry(content="temp"), branch_id="main")
        assert store.delete(mid, branch_id="main") is True
        ctx = store.retrieve("temp", branch_id="main")
        assert len(ctx.episodic_memories) == 0

    def test_empty_branch_retrieve(self) -> None:
        """T05: Retrieve from empty branch returns empty context."""
        store = FaissEpisodicStore()
        ctx = store.retrieve("anything", branch_id="nonexistent")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 0
        assert ctx.total_tokens == 0

    def test_add_with_empty_branch_raises(self) -> None:
        """T06: Adding with empty branch_id raises ValueError."""
        store = FaissEpisodicStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")

    def test_retrieve_updates_access_stats(self) -> None:
        """T07: Retrieve increments access_count and sets last_accessed."""
        store = FaissEpisodicStore()
        store.add(MemoryEntry(content="track me"), branch_id="main")
        ctx = store.retrieve("track me", branch_id="main")
        assert ctx.episodic_memories[0].access_count == 1
        assert ctx.episodic_memories[0].last_accessed is not None

    def test_conditional_id_generation(self) -> None:
        """T08: Conditional ID generation based on branch_id."""
        store = FaissEpisodicStore()
        mid1 = store.add(MemoryEntry(content="test"), branch_id="main")
        mid2 = store.add(MemoryEntry(content="test"), branch_id="therapist")
        assert mid1 != mid2
        assert mid1.startswith("faiss-")
        assert mid2.startswith("l2-faiss-")
