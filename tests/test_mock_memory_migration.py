"""Unit tests for MockMemoryMigrationService."""

import pytest

from chronopersona.mocks import MockMemoryMigrationService


class TestMockMemoryMigrationService:
    """Tests for MockMemoryMigrationService (W1 frozen mock)."""

    def test_migrate_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on migrate."""
        service = MockMemoryMigrationService()
        with pytest.raises(ValueError):
            service.migrate(source=None, target=None, branch_id="", filter_=None)

    def test_snapshot_returns_empty_dict(self) -> None:
        """snapshot returns empty dict."""
        service = MockMemoryMigrationService()
        result = service.snapshot(branch_id="main")
        assert result == {}

    def test_merge_branches_returns_merged_true(self) -> None:
        """merge_branches returns success indicator."""
        service = MockMemoryMigrationService()
        result = service.merge_branches(source_branch="a", target_branch="b")
        assert result == {"merged": True}

    def test_merge_branches_empty_source_raises(self) -> None:
        """Empty source or target branch raises ValueError."""
        service = MockMemoryMigrationService()
        with pytest.raises(ValueError):
            service.merge_branches(source_branch="", target_branch="b")
