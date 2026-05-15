"""Mock implementation of ICostTracker."""

from typing import Any

from chronopersona.contracts.interfaces import ICostTracker
from chronopersona.contracts.schemas import BudgetStatus


class MockCostTracker(ICostTracker):
    def record(
        self,
        request: Any,
        response: Any,
        latency_ms: float,
        branch_id: str,
    ) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

    def get_summary(
        self,
        scope: Any,
        branch_id: str,
        start: str,
        end: str,
    ) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return {}

    def check_budget(self, branch_id: str, session_id: str) -> BudgetStatus:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return BudgetStatus(branch_id=branch_id, session_id=session_id)
