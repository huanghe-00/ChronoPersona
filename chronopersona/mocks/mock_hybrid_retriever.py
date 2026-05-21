"""Mock hybrid retriever for testing."""

from chronopersona.contracts.interfaces import IHybridRetriever
from chronopersona.contracts.schemas import MemoryEntry, RetrievedContext


class MockHybridRetriever(IHybridRetriever):
    """Mock hybrid retriever returning fixed fused context."""

    def retrieve(
        self,
        query: str,
        branch_id: str,
        intent: str | None = None,
        top_k: int = 5,
    ) -> RetrievedContext:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return RetrievedContext(
            episodic_memories=[
                MemoryEntry(id="mock_hybrid_1", content="fused result"),
            ],
            total_tokens=12,
        )
