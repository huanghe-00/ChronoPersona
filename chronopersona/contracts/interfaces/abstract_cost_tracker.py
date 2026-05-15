"""[FUTURE] Cost tracking interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from chronopersona.contracts.schemas.model import BudgetStatus


class ICostTracker(ABC):
    """Model call cost tracking and budget enforcement.

    W1: Interface frozen. Mock returns empty pass.
    W5+: Integrated with ModelRouter.
    """

    @abstractmethod
    def record(
        self,
        request: Any,
        response: Any,
        latency_ms: float,
        branch_id: str,
    ) -> None:
        """Record a model call for cost tracking.

        Args:
            request: Original model request.
            response: Model response.
            latency_ms: End-to-end latency.
            branch_id: Branch context. Must not be empty.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def get_summary(
        self,
        scope: Any,
        branch_id: str,
        start: str,
        end: str,
    ) -> Any:
        """Retrieve cost summary for a scope and time range.

        Args:
            scope: Aggregation scope.
            branch_id: Branch to query. Must not be empty.
            start: ISO-8601 start timestamp.
            end: ISO-8601 end timestamp.

        Returns:
            CostSummary object.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def check_budget(self, branch_id: str, session_id: str) -> BudgetStatus:
        """Check current budget status for a session.

        Args:
            branch_id: Branch context. Must not be empty.
            session_id: Session identifier.

        Returns:
            BudgetStatus with consumption and warning level.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
