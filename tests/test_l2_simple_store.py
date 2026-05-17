"""Unit tests for SimpleEpisodicStore (Week 2 Day 3)."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic import SimpleEpisodicStore


class TestSimpleEpisodicStore:
    """T51-T55: SimpleEpisodicStore tests."""

    def test_add_and_retrieve_basic(self) -> None:
        """T51: Add and retrieve a memory entry."""
        store = SimpleEpisodicStore()
        entry = MemoryEntry(content="I like Sichuan food")
        mid = store.add(entry, branch_id="main")
        assert mid.startswith("l2-simple-")

        ctx = store.retrieve("Sichuan", branch_id="main")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("Sichuan" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """T52: Different branches have isolated memories."""
        store = SimpleEpisodicStore()
        store.add(MemoryEntry(content="secret"), branch_id="therapist")
        ctx = store.retrieve("secret", branch_id="rpg-hero")
        assert len(ctx.episodic_memories) == 0

    def test_retrieve_top_k_limit(self) -> None:
        """T53: Retrieve respects top_k limit."""
        store = SimpleEpisodicStore()
        for i in range(10):
            store.add(MemoryEntry(content=f"memory {i}"), branch_id="main")
        ctx = store.retrieve("memory", branch_id="main", top_k=3)
        assert len(ctx.episodic_memories) <= 3

    def test_delete_memory(self) -> None:
        """T54: Delete removes a memory entry."""
        store = SimpleEpisodicStore()
        mid = store.add(MemoryEntry(content="temp"), branch_id="main")
        assert store.delete(mid, branch_id="main") is True
        ctx = store.retrieve("temp", branch_id="main")
        assert len(ctx.episodic_memories) == 0

    def test_empty_branch_retrieve(self) -> None:
        """T55: Retrieve from empty branch returns empty context."""
        store = SimpleEpisodicStore()
        ctx = store.retrieve("anything", branch_id="nonexistent")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 0
        assert ctx.total_tokens == 0

    def test_add_with_empty_branch_raises(self) -> None:
        """T56: Adding with empty branch_id raises ValueError."""
        store = SimpleEpisodicStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")
