"""Unit tests for ConsolidationAgent."""

from typing import Any, Dict, List

import pytest

from chronopersona.contracts.interfaces import IConsolidationAgent
from chronopersona.memory_system.insight.consolidation_agent import ConsolidationAgent


class TestConsolidationAgent:
    """Tests for real ConsolidationAgent skeleton."""

    def test_should_trigger_true(self) -> None:
        """T01: should_trigger returns True for valid branch."""
        agent: IConsolidationAgent = ConsolidationAgent(None)
        assert agent.should_trigger("main") is True

    def test_should_trigger_empty_branch_raises(self) -> None:
        """T02: should_trigger with empty branch_id raises ValueError."""
        agent: IConsolidationAgent = ConsolidationAgent(None)
        with pytest.raises(ValueError):
            agent.should_trigger("")

    def test_consolidate_returns_empty_list(self) -> None:
        """T03: consolidate returns empty list in Phase B skeleton."""
        agent: IConsolidationAgent = ConsolidationAgent(None)
        rules: List[Dict[str, Any]] = agent.consolidate("main", top_k=5)
        assert rules == []

    def test_consolidate_empty_branch_raises(self) -> None:
        """T04: consolidate with empty branch_id raises ValueError."""
        agent: IConsolidationAgent = ConsolidationAgent(None)
        with pytest.raises(ValueError):
            agent.consolidate("", top_k=5)


class TestMockConsolidationAgent:
    """Tests for MockConsolidationAgent ensuring interface compliance."""

    def test_mock_is_instance_of_interface(self) -> None:
        """T05: MockConsolidationAgent is a valid IConsolidationAgent."""
        agent: IConsolidationAgent = MockConsolidationAgent()
        assert isinstance(agent, IConsolidationAgent)

    def test_mock_consolidate_returns_rule(self) -> None:
        """T06: Mock consolidate returns a fixed behavioral rule."""
        agent: IConsolidationAgent = MockConsolidationAgent()
        rules = agent.consolidate("main", top_k=3)
        assert len(rules) == 1
        assert rules[0]["confidence"] == 0.92

    def test_mock_tracks_calls(self) -> None:
        """T07: Mock records all operations for test assertions."""
        agent: MockConsolidationAgent = MockConsolidationAgent()
        agent.should_trigger("main")
        agent.consolidate("main", top_k=3)
        assert len(agent._calls) == 2
        assert agent._calls[0]["op"] == "should_trigger"
        assert agent._calls[1]["op"] == "consolidate"
