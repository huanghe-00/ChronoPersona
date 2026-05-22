"""Mock implementation of AbstractMemoryStore."""

from typing import Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractMemoryStore
from chronopersona.contracts.schemas import Fact, MemoryEntry, RetrievedContext, Snapshot, Version


class MockMemoryStore(AbstractMemoryStore):
    """In-memory mock memory store for testing and MVA development."""

    def __init__(self) -> None:
        self._memories: Dict[str, List[MemoryEntry]] = {}
        self._facts: Dict[str, List[Fact]] = {}
        self._versions: Dict[str, List[Version]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"mock-mem-{self._counter}"

    def add(self, memory: MemoryEntry, branch_id: str) -> str:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        mid = self._next_id()
        memory.id = mid
        self._memories.setdefault(branch_id, []).append(memory)
        return mid

    def retrieve(
        self,
        query: str,
        branch_id: str,
        intent: Optional[str] = None,
    ) -> RetrievedContext:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        memories = self._memories.get(branch_id, [])
        return RetrievedContext(
            working_memories=memories[-2:] if len(memories) >= 2 else memories,
            episodic_memories=memories,
            semantic_facts=self._facts.get(branch_id, []),
            total_tokens=sum(len(m.content) for m in memories),
        )

    def commit_version(self, branch_id: str) -> Version:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        v = Version(
            branch_id=branch_id,
            version=f"v-{len(self._versions.get(branch_id, []))}",
        )
        self._versions.setdefault(branch_id, []).append(v)
        return v

    def checkout_branch(
        self,
        branch_id: str,
        version: Optional[str] = None,
    ) -> Snapshot:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return Snapshot(branch_id=branch_id, version=version)

    def get_facts(self, entity_id: str, branch_id: str) -> List[Fact]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return [f for f in self._facts.get(branch_id, []) if f.entity_id == entity_id]

    def link_entities(
        self,
        source: str,
        target: str,
        relation: str,
        branch_id: str,
    ) -> bool:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return True
