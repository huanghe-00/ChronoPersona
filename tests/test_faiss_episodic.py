"""Tests for FaissEpisodicStore."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic import FaissEpisodicStore


class TestFaissEpisodicStore:
    """Tests for FAISS-backed episodic store."""

    def test_add_and_retrieve_basic(self) -> None:
        """Add entry and retrieve by query."""
        store = FaissEpisodicStore()
        entry = MemoryEntry(content="I like Sichuan food")
        mid = store.add(entry, branch_id="main")
        assert mid.startswith("faiss-")

        ctx = store.retrieve("Sichuan food", branch_id="main", top_k=5)
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("Sichuan" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """Different branches have isolated FAISS indices."""
        store = FaissEpisodicStore()
        store.add(MemoryEntry(content="secret"), branch_id="therapist")
        ctx = store.retrieve("secret", branch_id="rpg-hero")
        assert len(ctx.episodic_memories) == 0

    def test_top_k_limit(self) -> None:
        """Retrieve respects top_k limit."""
        store = FaissEpisodicStore()
        for i in range(10):
            store.add(MemoryEntry(content=f"memory {i}"), branch_id="main")
        ctx = store.retrieve("memory", branch_id="main", top_k=3)
        assert len(ctx.episodic_memories) <= 3

    def test_delete_soft(self) -> None:
        """Delete clears content via soft-delete."""
        store = FaissEpisodicStore()
        mid = store.add(MemoryEntry(content="temp"), branch_id="main")
        assert store.delete(mid, branch_id="main") is True
        ctx = store.retrieve("temp", branch_id="main")
        assert all(m.content != "temp" for m in ctx.episodic_memories)

    def test_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        store = FaissEpisodicStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")
