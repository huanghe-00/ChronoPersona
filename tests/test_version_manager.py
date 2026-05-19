"""Unit tests for version manager implementations."""

import pytest

from chronopersona.contracts.interfaces import AbstractVersionManager
from chronopersona.contracts.schemas import ChangeSet, Snapshot, Version
from chronopersona.mocks.mock_version_manager import MockVersionManager


class TestMockVersionManager:
    """Tests for MockVersionManager ensuring AbstractVersionManager compliance."""

    def test_commit_creates_version(self) -> None:
        """T01: commit creates a new version and increments counter."""
        vm: AbstractVersionManager = MockVersionManager()
        v = vm.commit("main", ChangeSet())
        assert isinstance(v, Version)
        assert v.branch_id == "main"
        assert "-v" in v.version

    def test_log_returns_committed_versions(self) -> None:
        """T02: log returns chronological list of committed versions."""
        vm: AbstractVersionManager = MockVersionManager()
        vm.commit("main", ChangeSet())
        vm.commit("main", ChangeSet())
        versions = vm.log("main")
        assert len(versions) == 2
        assert all(isinstance(v, Version) for v in versions)

    def test_checkout_returns_snapshot(self) -> None:
        """T03: checkout returns Snapshot with correct branch_id."""
        vm: AbstractVersionManager = MockVersionManager()
        snap = vm.checkout("main", version="v1")
        assert isinstance(snap, Snapshot)
        assert snap.branch_id == "main"
        assert snap.version == "v1"

    def test_checkout_empty_branch_raises_valueerror(self) -> None:
        """T04: checkout with empty branch_id raises ValueError."""
        vm: AbstractVersionManager = MockVersionManager()
        with pytest.raises(ValueError):
            vm.checkout("")

    def test_merge_returns_merge_result(self) -> None:
        """T05: merge returns MergeResult for valid branches."""
        vm: AbstractVersionManager = MockVersionManager()
        result = vm.merge("feature", "main")
        assert result.source_branch == "feature"
        assert result.target_branch == "main"

    def test_merge_empty_branch_raises_valueerror(self) -> None:
        """T06: merge with empty branch raises ValueError."""
        vm: AbstractVersionManager = MockVersionManager()
        with pytest.raises(ValueError):
            vm.merge("", "main")
        with pytest.raises(ValueError):
            vm.merge("main", "")

    def test_gc_removes_old_versions(self) -> None:
        """T07: gc retains keep_last_n versions and removes older ones."""
        vm: AbstractVersionManager = MockVersionManager()
        for _ in range(5):
            vm.commit("main", ChangeSet())
        removed = vm.gc("main", keep_last_n=2)
        assert removed == 3
        assert len(vm.log("main")) == 2

    def test_gc_keep_last_n_less_than_one_raises_valueerror(self) -> None:
        """T08: gc with keep_last_n < 1 raises ValueError."""
        vm: AbstractVersionManager = MockVersionManager()
        with pytest.raises(ValueError):
            vm.gc("main", keep_last_n=0)
