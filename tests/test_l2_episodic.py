"""Unit tests for L2 Episodic Memory (Week 2 Day 3)."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic import MockBGEEmbedder, MockEpisodicStore, SimpleEpisodicStore


class TestMockBGEEmbedder:
    """T43-T44: Embedder tests."""

    def test_embed_returns_correct_dimension(self) -> None:
        """T43: Embed returns vectors of expected dimension."""
        embedder = MockBGEEmbedder()
        vectors = embedder.embed(["hello", "world"])
        assert len(vectors) == 2
        assert all(len(v) == 128 for v in vectors)

    def test_embed_query_returns_vector(self) -> None:
        """T44: Embed query returns a single vector."""
        embedder = MockBGEEmbedder()
        vec = embedder.embed_query("test query")
        assert len(vec) == 128
        assert isinstance(vec, list)
        assert all(isinstance(x, float) for x in vec)


class TestMockEpisodicStore:
    """T45-T48: Episodic store tests."""

    def test_add_and_retrieve_basic(self) -> None:
        """T45: Add and retrieve a memory entry."""
        store = MockEpisodicStore()
        entry = MemoryEntry(content="I like Sichuan food")
        mid = store.add(entry, branch_id="main")
        assert mid.startswith("l2-mem-")

        ctx = store.retrieve("Sichuan", branch_id="main")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("Sichuan" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """T46: Different branches have isolated memories."""
        store = MockEpisodicStore()
        store.add(MemoryEntry(content="secret"), branch_id="therapist")
        ctx = store.retrieve("secret", branch_id="rpg-hero")
        assert len(ctx.episodic_memories) == 0

    def test_retrieve_top_k_limit(self) -> None:
        """T47: Retrieve respects top_k limit."""
        store = MockEpisodicStore()
        for i in range(10):
            store.add(MemoryEntry(content=f"memory {i}"), branch_id="main")
        ctx = store.retrieve("memory", branch_id="main", top_k=3)
        assert len(ctx.episodic_memories) <= 3

    def test_delete_memory(self) -> None:
        """T48: Delete removes a memory entry."""
        store = MockEpisodicStore()
        mid = store.add(MemoryEntry(content="temp"), branch_id="main")
        assert store.delete(mid, branch_id="main") is True
        ctx = store.retrieve("temp", branch_id="main")
        assert len(ctx.episodic_memories) == 0

    def test_empty_branch_retrieve(self) -> None:
        """T49: Retrieve from empty branch returns empty context."""
        store = MockEpisodicStore()
        ctx = store.retrieve("anything", branch_id="nonexistent")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 0
        assert ctx.total_tokens == 0

    def test_add_with_empty_branch_raises(self) -> None:
        """T50: Adding with empty branch_id raises ValueError."""
        store = MockEpisodicStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")

    def test_retrieve_updates_access_count_mock(self) -> None:
        """T56b: Mock retrieve also increments access_count."""
        store = MockEpisodicStore()
        store.add(MemoryEntry(content="mock track"), branch_id="main")
        ctx = store.retrieve("mock track", branch_id="main")
        assert ctx.episodic_memories[0].access_count == 1
        assert ctx.episodic_memories[0].last_accessed is not None


class TestSimpleEpisodicStore:
    """T51-T53: SimpleEpisodicStore (cosine similarity) tests."""

    def test_add_and_retrieve_basic(self) -> None:
        """T51: Add and retrieve a memory entry via cosine similarity."""
        store = SimpleEpisodicStore()
        entry = MemoryEntry(content="I enjoy hiking in the mountains")
        mid = store.add(entry, branch_id="main")
        assert mid.startswith("l2-simple-")

        ctx = store.retrieve("hiking", branch_id="main")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) >= 1
        assert any("hiking" in m.content for m in ctx.episodic_memories)

    def test_branch_isolation(self) -> None:
        """T52: Different branches are isolated."""
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

    def test_memory_entry_has_importance_fields(self) -> None:
        """T54: MemoryEntry has importance metadata with correct defaults."""
        entry = MemoryEntry(content="test")
        assert entry.importance == 0.5
        assert entry.access_count == 0
        assert entry.ttl_hours is None
        assert entry.last_accessed is None

    def test_retrieve_updates_access_stats(self) -> None:
        """T55: Retrieve increments access_count and sets last_accessed."""
        store = SimpleEpisodicStore()
        store.add(MemoryEntry(content="track me"), branch_id="main")
        ctx = store.retrieve("track me", branch_id="main")
        assert ctx.episodic_memories[0].access_count == 1
        assert ctx.episodic_memories[0].last_accessed is not None

    def test_importance_affects_ranking(self) -> None:
        """T56: Higher importance boosts ranking when similarity is equal."""
        store = SimpleEpisodicStore()
        store.add(MemoryEntry(content="common text", importance=0.1), branch_id="main")
        store.add(MemoryEntry(content="common text", importance=0.9), branch_id="main")
        ctx = store.retrieve("common text", branch_id="main", top_k=2)
        assert ctx.episodic_memories[0].importance == 0.9
