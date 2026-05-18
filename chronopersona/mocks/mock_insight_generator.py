"""Mock implementation of IInsightGenerator."""

from typing import List

from chronopersona.contracts.interfaces import IInsightGenerator
from chronopersona.contracts.schemas import Insight, MemoryEntry


class MockInsightGenerator(IInsightGenerator):
    """Mock insight generator returning fixed insights."""

    def generate(
        self,
        branch_id: str,
        recent_memories: List[MemoryEntry],
    ) -> List[Insight]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not recent_memories:
            return []
        return [
            Insight(
                id="insight-mock-001",
                insight_type="pattern",
                source_memory_ids=[m.id for m in recent_memories[:2]],
                content="Mock: user frequently mentions food preferences",
                confidence=0.85,
                branch_id=branch_id,
            ),
        ]

    def should_trigger(self, branch_id: str, turn_count_since_last: int) -> bool:
        return turn_count_since_last >= 10
