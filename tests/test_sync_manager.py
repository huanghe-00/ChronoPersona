"""Unit tests for SyncManager and MockSyncManager."""

from __future__ import annotations

import pytest

from chronopersona.memory_system.l0_crdt.lww_map import LWWEntry
from chronopersona.memory_system.l0_crdt.sync_manager import SyncManager
from chronopersona.mocks.mock_sync_manager import MockSyncManager


class TestSyncManager:
    """Tests for the concrete SyncManager."""

    def test_apply_remote_adds_entries(self) -> None:
        mgr = SyncManager(device_id="dev-a")
        remote = {
            "key1": LWWEntry(value="val1", timestamp=100, device_id="dev-b"),
        }
        conflicts = mgr.apply_remote(remote, branch_id="main")
        assert len(conflicts) == 0
        delta = mgr.get_delta("main")
        assert "key1" in delta
        assert delta["key1"].value == "val1"

    def test_checkpoint_clears_dirty_keys(self) -> None:
        mgr = SyncManager(device_id="dev-a")
        mgr.apply_remote(
            {"k1": LWWEntry(value="v1", timestamp=200, device_id="dev-b")},
            branch_id="main",
        )
        dirty_before = mgr.get_dirty_keys("main")
        assert "k1" in dirty_before
        persisted = mgr.checkpoint("main")
        assert "k1" in persisted
        assert mgr.get_dirty_keys("main") == []

    def test_empty_branch_raises(self) -> None:
        mgr = SyncManager(device_id="dev-a")
        with pytest.raises(ValueError):
            mgr.apply_remote({}, branch_id="")


class TestMockSyncManager:
    """Tests for the MockSyncManager."""

    def test_apply_remote_stores_entries(self) -> None:
        mock = MockSyncManager()
        remote = {
            "pref": LWWEntry(value="粤菜", timestamp=300, device_id="phone"),
        }
        conflicts = mock.apply_remote(remote, branch_id="main")
        assert conflicts == []
        delta = mock.get_delta("main")
        assert delta["pref"].value == "粤菜"

    def test_checkpoint_returns_dirty_keys(self) -> None:
        mock = MockSyncManager()
        mock._dirty["main"] = ["a", "b"]
        keys = mock.checkpoint("main")
        assert keys == ["a", "b"]
        assert mock.get_dirty_keys("main") == []

    def test_empty_branch_raises(self) -> None:
        mock = MockSyncManager()
        with pytest.raises(ValueError):
            mock.apply_remote({}, branch_id="")
