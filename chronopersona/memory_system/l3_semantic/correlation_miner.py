"""Simple correlation miner implementation."""

from typing import List

from chronopersona.contracts.interfaces.abstract_correlation_miner import (
    ICorrelationMiner,
)
from chronopersona.contracts.schemas import MemoryEntry


class SimpleCorrelationMiner(ICorrelationMiner):
    """Mine correlations based on keyword co-occurrence."""

    def mine_correlations(
        self,
        memories: List[MemoryEntry],
        branch_id: str,
        min_confidence: float = 0.6,
    ) -> List[str]:
        """Return correlated memory IDs using simple keyword overlap."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        correlated: List[str] = []
        for i, mem_a in enumerate(memories):
            for j, mem_b in enumerate(memories):
                if i >= j:
                    continue
                score = self.get_correlation_score(mem_a, mem_b, branch_id)
                if score >= min_confidence:
                    if mem_a.id and mem_a.id not in correlated:
                        correlated.append(mem_a.id)
                    if mem_b.id and mem_b.id not in correlated:
                        correlated.append(mem_b.id)
        return correlated

    def get_correlation_score(
        self,
        memory_a: MemoryEntry,
        memory_b: MemoryEntry,
        branch_id: str,
    ) -> float:
        """Compute correlation score based on shared keywords."""
        words_a = set(memory_a.content.split())
        words_b = set(memory_b.content.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
