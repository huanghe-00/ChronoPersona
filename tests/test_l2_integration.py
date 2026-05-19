"""Integration tests for L2 Episodic Memory layer.

Validates FaissEpisodicStore end-to-end write-retrieve pipeline,
including branch isolation and empty-branch edge cases.
"""

from __future__ import annotations

from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext
from chronopersona.memory_system.l2_episodic.faiss_store import FaissEpisodicStore


class TestL2EpisodicIntegration:
    """End-to-end integration tests for FaissEpisodicStore."""

    def test_faiss_write_and_retrieve(self) -> None:
        """T01: Written memories are retrievable via vector similarity."""
        store = FaissEpisodicStore(dim=128)
        entry = MemoryEntry(content="测试内容")
        memory_id = store.add(entry, branch_id="main")

        result = store.retrieve("测试", branch_id="main", top_k=5)

        assert isinstance(result, RetrievedContext)
        assert len(result.episodic_memories) >= 1
        assert any(m.content == "测试内容" for m in result.episodic_memories)
        assert memory_id.startswith("faiss-")

    def test_branch_isolation(self) -> None:
        """T02: Memories in branch A are invisible to branch B."""
        store = FaissEpisodicStore(dim=128)
        store.add(MemoryEntry(content="机密信息"), branch_id="secret")

        result = store.retrieve("机密", branch_id="public", top_k=5)

        assert result.episodic_memories == []
        assert result.total_tokens == 0

    def test_empty_branch_returns_empty(self) -> None:
        """T03: Retrieving from an empty or non-existent branch returns empty."""
        store = FaissEpisodicStore(dim=128)

        result = store.retrieve("任意查询", branch_id="void", top_k=5)

        assert result.episodic_memories == []
        assert result.total_tokens == 0
