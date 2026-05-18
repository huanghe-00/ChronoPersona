"""Tests for L3 SimpleSemanticStore."""

import pytest

from chronopersona.contracts.schemas import Fact
from chronopersona.memory_system.l3_semantic import SimpleSemanticStore


class TestSimpleSemanticStore:
    """Tests for in-memory semantic fact storage."""

    def test_add_and_get_fact(self) -> None:
        """Store and retrieve a structured fact."""
        store = SimpleSemanticStore()
        store.add_fact(Fact(entity_id="e1", attribute="name", value="Alice"), branch_id="main")
        facts = store.get_facts("e1", "main")
        assert len(facts) == 1
        assert facts[0].value == "Alice"

    def test_branch_isolation(self) -> None:
        """Facts are isolated by branch_id."""
        store = SimpleSemanticStore()
        store.add_fact(Fact(entity_id="e1", attribute="name", value="Alice"), branch_id="b1")
        assert len(store.get_facts("e1", "b2")) == 0

    def test_link_entities(self) -> None:
        """Entity linking returns True."""
        store = SimpleSemanticStore()
        assert store.link_entities("e1", "e2", "friend", "main") is True
        assert store.link_entities("e1", "e3", "colleague", "b1") is True
