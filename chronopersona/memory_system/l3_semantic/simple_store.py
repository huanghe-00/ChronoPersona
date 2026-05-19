"""Simple in-memory L3 semantic store."""

from __future__ import annotations

from typing import Dict, List

from chronopersona.contracts.interfaces import AbstractSemanticStore
from chronopersona.contracts.schemas import Fact


class SimpleSemanticStore(AbstractSemanticStore):
    """In-memory semantic store for facts and entity relationships."""

    def __init__(self) -> None:
        # branch_id -> list of facts
        self._facts: Dict[str, List[Fact]] = {}
        # branch_id -> list of relations
        self._relations: Dict[str, List[Dict[str, str]]] = {}

    def add_fact(self, fact: Fact, branch_id: str) -> None:
        """Store a structured fact."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._facts.setdefault(branch_id, []).append(fact)

    def get_facts(self, entity_id: str, branch_id: str) -> List[Fact]:
        """Retrieve facts for a given entity."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return [
            f for f in self._facts.get(branch_id, [])
            if f.entity_id == entity_id
        ]

    def link_entities(
        self,
        source: str,
        target: str,
        relation: str,
        branch_id: str,
    ) -> None:
        """Create a relationship between two entities."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._relations.setdefault(branch_id, []).append({
            "source": source,
            "target": target,
            "relation": relation,
        })
