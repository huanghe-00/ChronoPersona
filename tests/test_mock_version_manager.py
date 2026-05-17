"""Unit tests for MockVersionManager."""

import pytest

from chronopersona.contracts.schemas import ChangeSet, MergeResult, Snapshot, Version
from chronopersona.mocks import MockVersionManager


class TestMockVersionManager:
    """Tests for MockVersionManager."""

    def test_commit_returns_version(self) -> None:
        """Normal path: commit returns a Version with correct branch."""
        vm = MockVersionManager()
        v = vm.commit("main", ChangeSet())
        assert isinstance(v, Version)
        assert v.branch_id == "main"
        assert v.version.startswith("main-v")

    def test_commit_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.commit("", ChangeSet())

    def test_checkout_returns_snapshot(self) -> None:
        """checkout returns a Snapshot with correct branch."""
        vm = MockVersionManager()
        snap = vm.checkout("main")
        assert isinstance(snap, Snapshot)
        assert snap.branch_id == "main"

    def test_checkout_empty_branch_raises(self) -> None:
        """checkout with empty branch_id raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.checkout("")

    def test_merge_returns_merge_result(self) -> None:
        """merge returns MergeResult with source and target branches."""
        vm = MockVersionManager()
        result = vm.merge("source", "target")
        assert isinstance(result, MergeResult)
        assert result.source_branch == "source"
        assert result.target_branch == "target"

    def test_merge_empty_branches_raises(self) -> None:
        """merge with empty source or target raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.merge("", "target")
        with pytest.raises(ValueError):
            vm.merge("source", "")

    def test_log_returns_list_of_versions(self) -> None:
        """log returns a list of Version objects."""
        vm = MockVersionManager()
        vm.commit("main", ChangeSet())
        versions = vm.log("main")
        assert isinstance(versions, list)
        assert len(versions) == 1
        assert isinstance(versions[0], Version)

    def test_log_empty_branch_raises(self) -> None:
        """log with empty branch_id raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.log("")

    def test_gc_returns_removed_count(self) -> None:
        """gc returns number of removed versions."""
        vm = MockVersionManager()
        for _ in range(15):
            vm.commit("main", ChangeSet())
        removed = vm.gc("main", keep_last_n=5)
        assert removed == 10
        assert len(vm._versions["main"]) == 5

    def test_gc_empty_branch_raises(self) -> None:
        """gc with empty branch_id raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.gc("", keep_last_n=5)

    def test_gc_invalid_keep_last_n_raises(self) -> None:
        """gc with keep_last_n < 1 raises ValueError."""
        vm = MockVersionManager()
        with pytest.raises(ValueError):
            vm.gc("main", keep_last_n=0)
