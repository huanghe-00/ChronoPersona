"""Tests for VLNAgent: command parsing and navigation integration.

Covers:
- Chinese navigation command parsing
- Unknown/empty command handling
- Follow-up generation
- Integration with MockEmbodiedAdapter
"""

import pytest

from chronopersona.contracts.schemas import (
    NavigationResult,
    SemanticNavigationGoal,
)
from chronopersona.embodied.vln_agent import VLNAgent
from chronopersona.mocks.mock_embodied_adapter import MockEmbodiedAdapter


class TestVLNCommandParsing:
    """Verify natural language command parsing."""

    def setup_method(self) -> None:
        self.agent = VLNAgent()

    def test_parse_go_to_sofa(self):
        """'请到沙发旁边' → target_object='沙发'."""
        goal = self.agent.parse_command("请到沙发旁边")
        assert goal is not None
        assert goal.target_object == "沙发"

    def test_parse_navigate_to_bed(self):
        """'去床那边' → target_object='床'."""
        goal = self.agent.parse_command("去床那边")
        assert goal is not None
        assert goal.target_object == "床"

    def test_parse_find_table(self):
        """'找到桌子' → target_object='桌子'."""
        goal = self.agent.parse_command("找到桌子")
        assert goal is not None
        assert goal.target_object == "桌子"

    def test_parse_empty_returns_none(self):
        """Empty string returns None."""
        assert self.agent.parse_command("") is None

    def test_parse_non_nav_returns_none(self):
        """Non-navigation text returns None."""
        assert self.agent.parse_command("今天天气不错") is None

    def test_parse_unknown_object_returns_none(self):
        """Navigation to unknown object returns None (no match in dict)."""
        # "去飞船" has nav pattern but "飞船" is not in _NAV_TARGETS
        assert self.agent.parse_command("去飞船") is None


class TestVLNNavigationExecution:
    """Verify end-to-end navigation with MockEmbodiedAdapter."""

    def setup_method(self) -> None:
        self.mock_adapter = MockEmbodiedAdapter()
        self.agent = VLNAgent(adapter=self.mock_adapter)

    def test_execute_nav_sofa_success(self):
        """Navigate to sofa via mock adapter returns success."""
        result = self.agent.execute_navigation("请到沙发旁边", branch_id="main")
        assert isinstance(result, NavigationResult)
        assert result.success is True

    def test_execute_empty_branch_raises(self):
        """Empty branch_id raises ValueError."""
        with pytest.raises(ValueError, match="branch_id must not be empty"):
            self.agent.execute_navigation("去沙发", branch_id="")

    def test_execute_no_adapter_raises(self):
        """No adapter configured raises RuntimeError."""
        agent = VLNAgent()
        with pytest.raises(RuntimeError, match="No embodied adapter"):
            agent.execute_navigation("去沙发", branch_id="main")

    def test_execute_non_nav_returns_failure(self):
        """Non-navigation command returns failed NavigationResult."""
        result = self.agent.execute_navigation("你好", branch_id="main")
        assert result.success is False
        assert result.steps_taken == 0


class TestVLNFollowUp:
    """Verify follow-up question generation."""

    def setup_method(self) -> None:
        self.agent = VLNAgent()

    def test_follow_up_success(self):
        """Successful navigation produces helpful follow-up."""
        result = NavigationResult(success=True, steps_taken=10)
        text = self.agent.generate_follow_up(result)
        assert "还需要" in text

    def test_follow_up_failure(self):
        """Failed navigation produces retry prompt."""
        result = NavigationResult(success=False, steps_taken=50)
        text = self.agent.generate_follow_up(result)
        assert "未能" in text or "重新" in text
