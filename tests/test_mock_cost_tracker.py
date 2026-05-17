"""Unit tests for MockCostTracker."""

import pytest

from chronopersona.contracts.schemas import BudgetStatus
from chronopersona.mocks import MockCostTracker


class TestMockCostTracker:
    """Tests for MockCostTracker (W1 frozen mock)."""

    def test_record_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on record."""
        tracker = MockCostTracker()
        with pytest.raises(ValueError):
            tracker.record(None, None, 0.0, branch_id="")

    def test_get_summary_returns_empty_dict(self) -> None:
        """get_summary returns empty dict for valid branch."""
        tracker = MockCostTracker()
        result = tracker.get_summary(
            scope="session", branch_id="main", start="2024-01-01", end="2024-12-31"
        )
        assert result == {}

    def test_check_budget_returns_budget_status(self) -> None:
        """check_budget returns BudgetStatus with correct fields."""
        tracker = MockCostTracker()
        status = tracker.check_budget(branch_id="main", session_id="s1")
        assert isinstance(status, BudgetStatus)
        assert status.branch_id == "main"
        assert status.session_id == "s1"

    def test_check_budget_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on check_budget."""
        tracker = MockCostTracker()
        with pytest.raises(ValueError):
            tracker.check_budget(branch_id="", session_id="s1")
