"""Interface for semantic edge builders."""

from abc import ABC, abstractmethod
from typing import List

from chronopersona.contracts.schemas.semantic import SemanticEdge


class IEdgeBuilder(ABC):
    """Build semantic edges from a single dialog turn.

    Tier 1: Rule-based (MVA). Tier 2/3: [FUTURE].
    """

    @abstractmethod
    def build_edges(
        self,
        turn_id: str,
        session_id: str,
        branch_id: str,
        content: str,
        entities: List[str],
        prev_turn_id: str | None = None,
    ) -> List[SemanticEdge]:
        """Extract and build edges from one turn.

        Returns:
            List of edges to be inserted into IntentGraph.

        Raises:
            ValueError: If branch_id or turn_id is empty.
        """

    @abstractmethod
    def supported_types(self) -> List[str]:
        """Return edge types this builder can produce."""
