"""Mock implementation of ICorrelationMiner."""

from typing import List

from chronopersona.contracts.interfaces.abstract_correlation_miner import (
    ICorrelationMiner,
)
from chronopersona.contracts.schemas import MemoryEntry


class MockCorrelationMiner(ICorrelationMiner):
    """Mock correlation miner that returns predefined results."""

    def __init__(self) -> None:
        self._correlated_ids: List[str] = []
        self._score_map: dict[tuple[str, str], float] = {}

    def set_correlated_ids(self, ids: List[str]) -> None:
        """Predefine which memory IDs are correlated."""
        self._correlated_ids = list(ids)

    def set_score(self, id_a: str, id_b: str, score: float) -> None:
        """Predefine correlation score for a pair."""
        self._score_map[(id_a, id_b)] = score
        self._score_map[(id_b, id_a)] = score

    def mine_correlations(
        self,
        memories: List[MemoryEntry],
        branch_id: str,
        min_confidence: float = 0.6,
    ) -> List[str]:
        """Return predefined correlated IDs."""
        return self._correlated_ids

    def get_correlation_score(
        self,
        memory_a: MemoryEntry,
        memory_b: MemoryEntry,
        branch_id: str,
    ) -> float:
        """Return predefined correlation score."""
        return self._score_map.get(
            (memory_a.id, memory_b.id), 0.0
        )
