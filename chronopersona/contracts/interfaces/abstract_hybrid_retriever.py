"""Interface for hybrid retrieval (vector + graph + keyword)."""

from abc import ABC, abstractmethod

from chronopersona.contracts.schemas import RetrievedContext


class IHybridRetriever(ABC):
    """Orchestrate L2 vector, L3 graph, and fast-path keyword recall.

    MVA fusion: interleave episodic + graph results, deduplicate by memory_id.
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        branch_id: str,
        intent: str | None = None,
        top_k: int = 5,
    ) -> RetrievedContext:
        """Execute hybrid retrieval and return fused context.

        Args:
            query: Raw user query.
            branch_id: Explicit branch.
            intent: Optional intent type for graph navigation.
            top_k: Max total results.

        Raises:
            ValueError: If branch_id is empty.
        """
