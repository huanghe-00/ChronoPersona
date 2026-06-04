"""Simple episodic memory store with A-MAC admission control.

v0.7.0: Implements Adaptive Memory Admission Control (A-MAC)
with TypePrior weights and two-tier threshold gating.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from loguru import logger


# TypePrior weights per requirements.md 4.14.1
TYPE_PRIOR_WEIGHTS: Dict[str, float] = {
    "procedural": 1.0,
    "preference": 0.9,
    "fact": 0.6,
    "chitchat": 0.1,
}

# A-MAC thresholds
ADMISSION_THRESHOLD_L2_L3 = 0.65
ADMISSION_THRESHOLD_L2_ONLY = 0.40


@dataclass
class AdmissionResult:
    """Result of A-MAC gate evaluation."""
    score: float
    route: str  # "discard", "l2_only", "l2_l3"
    reason: str


class SimpleEpisodicStore:
    """In-memory episodic store with A-MAC admission gating."""

    def __init__(self) -> None:
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._branch_index: Dict[str, List[str]] = {}

    def add(
        self,
        memory: Dict[str, Any],
        branch_id: str,
        memory_type: str = "episodic",
    ) -> Optional[str]:
        """Add memory with A-MAC admission control.

        Returns memory_id if admitted, None if discarded.
        """
        admission = self._evaluate_admission(memory, memory_type)
        logger.info(
            "A-MAC: score={:.3f} route={} reason={}",
            admission.score,
            admission.route,
            admission.reason,
        )

        if admission.route == "discard":
            logger.debug("Memory discarded by A-MAC gate")
            return None

        memory_id = memory.get("id", f"mem_{len(self._memories)}")
        memory["admission_score"] = admission.score
        memory["branch_id"] = branch_id
        memory["memory_type"] = memory_type

        self._memories[memory_id] = memory
        if branch_id not in self._branch_index:
            self._branch_index[branch_id] = []
        self._branch_index[branch_id].append(memory_id)

        return memory_id

    def _evaluate_admission(
        self,
        memory: Dict[str, Any],
        memory_type: str,
    ) -> AdmissionResult:
        """Compute A-MAC admission score and routing decision."""
        importance = float(memory.get("importance", 0.5))
        access_count = int(memory.get("access_count", 0))
        ttl_hours = float(memory.get("ttl_hours", 24.0)) if memory.get("ttl_hours") else 24.0

        # TypePrior weight
        type_prior = TYPE_PRIOR_WEIGHTS.get(memory_type, 0.5)

        # Simplified A-MAC: importance * type_prior * recency_factor
        recency_factor = min(1.0, 1.0 / (1.0 + max(0, ttl_hours / 168.0)))  # weekly decay
        score = importance * type_prior * (1.0 + 0.1 * min(access_count, 10)) * recency_factor

        if score >= ADMISSION_THRESHOLD_L2_L3:
            route = "l2_l3"
            reason = "high importance + type priority"
        elif score >= ADMISSION_THRESHOLD_L2_ONLY:
            route = "l2_only"
            reason = "moderate importance, L2 only"
        else:
            route = "discard"
            reason = "low importance or chitchat"

        return AdmissionResult(score=score, route=route, reason=reason)

    def retrieve(
        self,
        query: str,
        branch_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based retrieval (MVA baseline)."""
        branch_memories = [
            self._memories[mid]
            for mid in self._branch_index.get(branch_id, [])
            if mid in self._memories
        ]
        # Simple scoring: keyword overlap
        query_words = set(query.lower().split())
        scored = []
        for mem in branch_memories:
            content = str(mem.get("content", ""))
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((overlap, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:top_k]]
