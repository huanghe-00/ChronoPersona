"""Unit tests for L0 LWW-CRDT core (Week 2 Day 1)."""

import pytest

from chronopersona.memory_system.l0_crdt import (
    ClockSkewConflict,
    HybridTimestamp,
    LWWEntry,
    LWWMap,
)


class TestHybridTimestamp:
    """T32-T34: HLC ordering basics."""

    def test_hlc_physical_ordering(self) -> None:
        """T32: Larger physical time wins."""
        t1 = HybridTimestamp(100, 0)
        t2 = HybridTimestamp(200, 0)
        assert t1 < t2
        assert t2 > t1

    def test_hlc_logical_tiebreak(self) -> None:
        """T33: Equal physical time uses logical counter."""
        t1 = HybridTimestamp(100, 0)
        t2 = HybridTimestamp(100, 1)
        assert t1 < t2
        assert t2 > t1

    def test_hlc_equality(self) -> None:
        """T34: Equal physical and logical are equivalent."""
        t1 = HybridTimestamp(100, 5)
        t2 = HybridTimestamp(100, 5)
        assert t1 == t2
        assert not (t1 < t2)
        assert not (t1 > t2)


class TestLWWMap:
    """T35-T37: LWWMap core semantics."""

    def test_set_and_get_basic(self) -> None:
        """T35: Basic set/get roundtrip."""
        lww = LWWMap("dev-a")
        ts = HybridTimestamp.now()
        lww.set("pref", "川菜", ts)
        assert lww.get("pref") == "川菜"

    def test_add_wins_merge(self) -> None:
        """T36: Merge adopts remote winner by HLC."""
        lww = LWWMap("dev-a")
        lww.set("k", "local_v", HybridTimestamp(100, 0))
        remote = {"k": LWWEntry("remote_v", HybridTimestamp(200, 0), "dev-b")}
        conflicts = lww.merge(remote)
        assert lww.get("k") == "remote_v"
        assert conflicts == []

    def test_clock_skew_detected(self) -> None:
        """T37: Skew > 500ms triggers conflict record."""
        lww = LWWMap("dev-a")
        base = 1_000_000_000
        lww.set("k", "local", HybridTimestamp(base, 0))
        # 1 second difference > 500ms MAX_CLOCK_SKEW_NS
        remote = {
            "k": LWWEntry("remote", HybridTimestamp(base + 1_000_000_000, 0), "dev-b")
        }
        conflicts = lww.merge(remote)
        assert len(conflicts) == 1
        assert conflicts[0].key == "k"
        assert isinstance(conflicts[0], ClockSkewConflict)
        # Map still holds add-wins winner (remote has larger HLC)
        assert lww.get("k") == "remote"
