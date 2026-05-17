"""Unit tests for MockSkillRegistry."""

import pytest

from chronopersona.mocks import MockSkillRegistry


class TestMockSkillRegistry:
    """Tests for MockSkillRegistry (W1 frozen mock)."""

    def test_register_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on register."""
        registry = MockSkillRegistry()
        with pytest.raises(ValueError):
            registry.register(skill=None, branch_id="")

    def test_execute_returns_mock_executed(self) -> None:
        """execute returns mock status dict."""
        registry = MockSkillRegistry()
        result = registry.execute(skill_id="s1", params={}, branch_id="main")
        assert result == {"status": "mock_executed"}

    def test_get_available_skills_returns_empty_list(self) -> None:
        """get_available_skills returns empty list."""
        registry = MockSkillRegistry()
        skills = registry.get_available_skills(branch_id="main", persona_id="p1")
        assert skills == []

    def test_execute_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on execute."""
        registry = MockSkillRegistry()
        with pytest.raises(ValueError):
            registry.execute(skill_id="s1", params={}, branch_id="")
