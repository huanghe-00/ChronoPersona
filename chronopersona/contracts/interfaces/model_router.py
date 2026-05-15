"""Abstract Model Router interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from chronopersona.contracts.schemas.model import CostReport, ModelRequest, ModelResponse


class AbstractModelRouter(ABC):
    """Abstract interface for model routing and cost tracking.

    Responsible for task-to-model mapping, API failover,
    cache management, and cost accounting.
    All operations require an explicit branch_id.
    """

    @abstractmethod
    def route(self, request: ModelRequest, branch_id: str) -> ModelResponse:
        """Route a request to the appropriate model and execute.

        Args:
            request: Structured model request.
            branch_id: Branch context for isolation and cost attribution.
                Must not be empty.

        Returns:
            ModelResponse containing generated content and usage stats.

        Raises:
            ValueError: If branch_id is empty.
            RuntimeError: If all model providers fail.
        """
        ...

    @abstractmethod
    def get_cost_summary(self, branch_id: str) -> CostReport:
        """Retrieve aggregated cost report for a branch.

        Args:
            branch_id: Branch to query. Must not be empty.

        Returns:
            CostReport with token usage and latency breakdowns.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def cache_clear(self, branch_id: str) -> None:
        """Clear the prompt cache for a branch.

        Args:
            branch_id: Target branch. Must not be empty.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
