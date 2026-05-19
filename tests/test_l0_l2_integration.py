"""Integration tests for L0-L2 memory layers and Session-MVCC."""

import pytest

from chronopersona.agent_core import StateMachineAgentCore
from chronopersona.memory_system.l0_crdt import HybridTimestamp, L0SyncLayer, LWWEntry
from chronopersona.mocks import MockMemoryStore, MockModelRouter, MockVersionManager


class TestL0L2Integration:
    """Tests verifying L0 CRDT behavior and session snapshot integration."""

    def test_l0_merge_creates_conflict_record(self) -> None:
        """L0 merge with clock skew should record conflict for upstream CONTRADICTS."""
        l0 = L0SyncLayer(device_id="dev-a")
        l0.set("pref", "川菜", branch_id="main", device_id="dev-a")
        local_ts = l0._get_map("main").get_entry("pref").timestamp
        remote = {
            "pref": LWWEntry(
                value="粤菜",
                timestamp=HybridTimestamp(local_ts.physical + 1_000_000_000, 0),
                device_id="dev-b",
            )
        }
        conflicts = l0.merge(remote, branch_id="main")
        assert "pref" in conflicts
        assert l0.get("pref", branch_id="main") == "粤菜"

    def test_session_snapshot_via_agent_core(self) -> None:
        """AgentCore commit_session_snapshot should create a version."""
        vm = MockVersionManager()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            version_manager=vm,
        )
        v = core.commit_session_snapshot("main")
        assert v.branch_id == "main"
        # Verify that a version was created (MockVersionManager tracks internally)
        assert len(vm.versions) >= 1

    def test_persona_switch_commits_snapshot(self) -> None:
        """switch_persona should auto-commit snapshot when version_manager available."""
        vm = MockVersionManager()
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            version_manager=vm,
        )
        core.switch_persona("therapist", branch_id="main")
        # Verify that a version was created (MockVersionManager tracks internally)
        assert len(vm.versions) >= 1

    def test_l0_branch_isolation(self) -> None:
        """L0 data is strictly isolated by branch_id."""
        l0 = L0SyncLayer(device_id="dev-a")
        l0.set("key", "branch-a-value", branch_id="branch-a", device_id="dev-a")
        assert l0.get("key", branch_id="branch-a") == "branch-a-value"
        assert l0.get("key", branch_id="branch-b") is None
