"""Mock consolidation agent for testing."""

from typing import Any, Dict, List

from chronopersona.contracts.interfaces import IConsolidationAgent


class MockConsolidationAgent(IConsolidationAgent):
    """Mock consolidation agent returning fixed rules and tracking calls."""

    def __init__(self) -> None:
        self._calls: List[Dict[str, Any]] = []

    def should_trigger(self, branch_id: str) -> bool:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._calls.append({"op": "should_trigger", "branch_id": branch_id})
        return True

    def consolidate(self, branch_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        self._calls.append(
            {"op": "consolidate", "branch_id": branch_id, "top_k": top_k}
        )
        return [
            {
                "trigger": "user_mentions_performance",
                "action": "suggest_flame_graph",
                "confidence": 0.92,
            }
        ]
