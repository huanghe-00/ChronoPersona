"""Unit tests for L0 LWW-CRDT sync layer."""

from typing import Any, Dict

import pytest

from chronopersona.contracts.interfaces import AbstractL0SyncLayer
from chronopersona.memory_system.l0_crdt.sync_layer import L0SyncLayer
from chronopersona.mocks.mock_l0_sync import MockL0SyncLayer


class TestL0SyncLayerReal:
    """Tests for production L0SyncLayer backed by LWWMap."""

    def test_get_set_basic(self) -> None:
        """T01: set and get a key within a branch."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        sync.set("pref", "川菜", branch_id="main", device_id="phone-a")
        assert sync.get("pref", branch_id="main") == "川菜"

    def test_branch_isolation(self) -> None:
        """T02: keys must not leak across branches."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        sync.set("k1", "v1", branch_id="branch-a", device_id="dev-1")
        assert sync.get("k1", branch_id="branch-b") is None

    def test_empty_branch_raises_valueerror(self) -> None:
        """T03: empty branch_id or device_id raises ValueError."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        with pytest.raises(ValueError):
            sync.set("k", "v", branch_id="", device_id="dev")
        with pytest.raises(ValueError):
            sync.get("k", branch_id="")

    def test_checkpoint_returns_dirty_keys(self) -> None:
        """T04: checkpoint flushes dirty keys and returns them."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        sync.set("k1", "v1", branch_id="main", device_id="dev-a")
        sync.set("k2", "v2", branch_id="main", device_id="dev-a")
        keys: List[str] = sync.checkpoint("main")
        assert "k1" in keys
        assert "k2" in keys

    def test_get_delta_full_state_when_no_vector_clock(self) -> None:
        """T05: get_delta without vector clock returns full state."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        sync.set("k1", "v1", branch_id="main", device_id="dev-a")
        delta: Dict[str, Any] = sync.get_delta("main")
        assert "k1" in delta

    def test_merge_rejects_non_lww_entry_values(self) -> None:
        """T06: merge raises TypeError when remote_state contains raw values."""
        sync: AbstractL0SyncLayer = L0SyncLayer(device_id="test-device")
        sync.set("pref", "local", branch_id="main", device_id="dev-a")
        with pytest.raises(TypeError):
            sync.merge({"pref": "remote"}, branch_id="main")


class TestMockL0SyncLayer:
    """Tests for MockL0SyncLayer ensuring it satisfies AbstractL0SyncLayer."""

    def test_mock_is_instance_of_interface(self) -> None:
        """T07: MockL0SyncLayer is a valid AbstractL0SyncLayer."""
        sync: AbstractL0SyncLayer = MockL0SyncLayer()
        assert isinstance(sync, AbstractL0SyncLayer)

    def test_mock_merge_remote_wins(self) -> None:
        """T08: Mock merge unconditionally overwrites local with remote."""
        sync: AbstractL0SyncLayer = MockL0SyncLayer()
        sync.set("pref", "川菜", branch_id="main", device_id="phone")
        conflicts: Dict[str, Any] = sync.merge({"pref": "粤菜"}, branch_id="main")
        assert "pref" in conflicts
        assert sync.get("pref", branch_id="main") == "粤菜"
