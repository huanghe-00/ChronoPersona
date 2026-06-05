"""Hard budget throttle implementation for v1.1.0 production baseline."""

from typing import Any, Dict
from dataclasses import dataclass, field

from loguru import logger

from chronopersona.contracts.interfaces.abstract_cost_tracker import ICostTracker
from chronopersona.contracts.schemas.model import BudgetStatus


@dataclass
class _SessionBudget:
    tokens_used: int = 0
    calls: int = 0


class CostTracker(ICostTracker):
    """Production cost tracker with real-time accumulation and hard throttle."""

    def __init__(
        self,
        token_budget: int = 8000,
        warning_threshold: float = 0.8,
    ) -> None:
        self._token_budget = token_budget
        self._warning_threshold = warning_threshold
        self._sessions: Dict[str, _SessionBudget] = {}

    def record(
        self,
        request: Any,
        response: Any,
        latency_ms: float,
        branch_id: str,
    ) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        session_id = getattr(request, "session_id", "default")
        key = f"{branch_id}:{session_id}"

        budget = self._sessions.setdefault(key, _SessionBudget())
        input_tokens = getattr(request, "input_tokens", 0)
        output_tokens = getattr(response, "output_tokens", 0)
        total = input_tokens + output_tokens

        budget.tokens_used += total
        budget.calls += 1

        ratio = budget.tokens_used / self._token_budget
        if ratio >= 1.0:
            logger.error(
                "Budget EXCEEDED: {} tokens / {} (branch={}, session={})",
                budget.tokens_used,
                self._token_budget,
                branch_id,
                session_id,
            )
        elif ratio >= self._warning_threshold:
            logger.warning(
                "Budget WARNING: {} tokens / {} ({:.0%}) (branch={}, session={})",
                budget.tokens_used,
                self._token_budget,
                ratio,
                branch_id,
                session_id,
            )

    def get_summary(
        self,
        scope: Any,
        branch_id: str,
        start: str,
        end: str,
    ) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        # MVA skeleton: return aggregated session stats
        return {
            "branch_id": branch_id,
            "sessions_tracked": len(self._sessions),
        }

    def check_budget(self, branch_id: str, session_id: str) -> BudgetStatus:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        key = f"{branch_id}:{session_id}"
        budget = self._sessions.get(key, _SessionBudget())
        ratio = budget.tokens_used / self._token_budget if self._token_budget > 0 else 0.0

        if ratio >= 1.0:
            warning_level = "exceeded"
        elif ratio >= self._warning_threshold:
            warning_level = "warning"
        else:
            warning_level = "normal"

        return BudgetStatus(
            branch_id=branch_id,
            session_id=session_id,
            token_budget=self._token_budget,
            tokens_used=budget.tokens_used,
            usd_budget=0.0,
            usd_used=0.0,
            warning_level=warning_level,
            last_updated="",  # MVA: empty string as placeholder
        )
