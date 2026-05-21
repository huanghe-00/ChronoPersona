"""Mock edge builder for testing."""

from typing import List

from chronopersona.contracts.interfaces import IEdgeBuilder
from chronopersona.contracts.schemas.semantic import SemanticEdge


class MockEdgeBuilder(IEdgeBuilder):
    """Mock edge builder returning fixed edges."""

    def supported_types(self) -> List[str]:
        return ["MENTIONS", "TEMPORAL_NEXT"]

    def build_edges(
        self,
        turn_id: str,
        session_id: str,
        branch_id: str,
        content: str,
        entities: List[str],
        prev_turn_id: str | None = None,
    ) -> List[SemanticEdge]:
        if not branch_id or not turn_id:
            raise ValueError("branch_id and turn_id must not be empty")
        return [
            SemanticEdge(
                id=f"mock_{turn_id}_e1",
                source_id=turn_id,
                target_id="mock_entity",
                edge_type="MENTIONS",
                branch_id=branch_id,
            )
        ]
