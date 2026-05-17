"""Unit tests for L0 CRDT Sync Layer real implementation."""

import pytest

from chronopersona.memory_system.l0_crdt import (
    HybridTimestamp,
    L0SyncLayer,
    LWWEntry,
)


class TestL0SyncLayer:
    """Tests for L0SyncLayer backed by LWWMap."""

    def test_set_get_roundtrip(self) -> None:
        """Set value and retrieve it."""
        sync = L0SyncLayer(device_id="dev-a")
        sync.set("key1", "value1", branch_id="main", device_id="dev-a")
        assert sync.get("key1", branch_id="main") == "value1"

    def test_merge_detects_conflict(self) -> None:
        """Merge with remote entry having large clock skew triggers conflict."""
        sync = L0SyncLayer(device_id="dev-a")
        sync.set("k", "local", branch_id="main", device_id="dev-a")
        local_ts = HybridTimestamp.now()
        remote = {
            "k": LWWEntry(
                value="remote",
                timestamp=HybridTimestamp(local_ts.physical + 1_000_000_000, 0),
                device_id="dev-b",
            )
        }
        conflicts = sync.merge(remote, branch_id="main")
        assert "k" in conflicts
        # add-wins: remote has larger HLC
        assert sync.get("k", branch_id="main") == "remote"

    def test_branch_isolation(self) -> None:
        """Data in one branch is not visible in another."""
        sync = L0SyncLayer(device_id="dev-a")
        sync.set("key", "branch-a-value", branch_id="branch-a", device_id="dev-a")
        assert sync.get("key", branch_id="branch-a") == "branch-a-value"
        assert sync.get("key", branch_id="branch-b") is None

    def test_checkpoint_returns_dirty_keys(self) -> None:
        """Checkpoint returns keys modified since last checkpoint."""
        sync = L0SyncLayer(device_id="dev-a")
        sync.set("k1", "v1", branch_id="main", device_id="dev-a")
        sync.set("k2", "v2", branch_id="main", device_id="dev-a")
        keys = sync.checkpoint("main")
        assert set(keys) == {"k1", "k2"}
        # Second checkpoint should be empty
        assert sync.checkpoint("main") == []

    def test_empty_branch_id_raises(self) -> None:
        """Empty branch_id raises ValueError on set/get."""
        sync = L0SyncLayer(device_id="dev-a")
        with pytest.raises(ValueError):
            sync.set("k", "v", branch_id="", device_id="dev-a")
        with pytest.raises(ValueError):
            sync.get("k", branch_id="")
