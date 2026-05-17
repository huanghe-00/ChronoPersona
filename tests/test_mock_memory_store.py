"""Unit tests for MockMemoryStore."""

import pytest

from chronopersona.contracts.schemas import (
    Fact,
    MemoryEntry,
    RetrievedContext,
    Snapshot,
    Version,
)
from chronopersona.mocks import MockMemoryStore


class TestMockMemoryStore:
    """Tests for MockMemoryStore."""

    def test_add_returns_memory_id(self) -> None:
        """Normal path: add returns a string id and stores the entry."""
        store = MockMemoryStore()
        mid = store.add(MemoryEntry(content="test"), branch_id="main")
        assert isinstance(mid, str)
        assert mid.startswith("mock-mem-")

    def test_add_empty_branch_raises(self) -> None:
        """add with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(content="test"), branch_id="")

    def test_retrieve_returns_retrieved_context(self) -> None:
        """retrieve returns RetrievedContext with stored memories."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="hello"), branch_id="main")
        ctx = store.retrieve("hello", branch_id="main")
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 1
        assert ctx.episodic_memories[0].content == "hello"

    def test_retrieve_empty_branch_raises(self) -> None:
        """retrieve with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.retrieve("query", branch_id="")

    def test_commit_version_returns_version(self) -> None:
        """commit_version returns a Version with correct branch."""
        store = MockMemoryStore()
        v = store.commit_version("main")
        assert isinstance(v, Version)
        assert v.branch_id == "main"

    def test_commit_version_empty_branch_raises(self) -> None:
        """commit_version with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.commit_version("")

    def test_checkout_branch_returns_snapshot(self) -> None:
        """checkout_branch returns a Snapshot with correct branch."""
        store = MockMemoryStore()
        snap = store.checkout_branch("main")
        assert isinstance(snap, Snapshot)
        assert snap.branch_id == "main"

    def test_checkout_branch_empty_branch_raises(self) -> None:
        """checkout_branch with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.checkout_branch("")

    def test_get_facts_returns_list(self) -> None:
        """get_facts returns a list of Fact objects."""
        store = MockMemoryStore()
        facts = store.get_facts("entity-1", branch_id="main")
        assert isinstance(facts, list)
        # Mock returns empty list by default
        assert facts == []

    def test_get_facts_empty_branch_raises(self) -> None:
        """get_facts with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.get_facts("entity-1", branch_id="")

    def test_link_entities_returns_true(self) -> None:
        """link_entities returns True for valid arguments."""
        store = MockMemoryStore()
        result = store.link_entities("e1", "e2", "knows", branch_id="main")
        assert result is True

    def test_link_entities_empty_branch_raises(self) -> None:
        """link_entities with empty branch_id raises ValueError."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.link_entities("e1", "e2", "knows", branch_id="")
