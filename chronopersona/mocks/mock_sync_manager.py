"""Mock implementation of AbstractSyncManager for testing."""

from __future__ import annotations

from typing import Dict, List, Optional

from chronopersona.contracts.interfaces.abstract_sync_manager import AbstractSyncManager
from chronopersona.memory_system.l0_crdt.lww_map import ClockSkewConflict, LWWEntry


class MockSyncManager(AbstractSyncManager):
    """In-memory sync manager that records calls for test assertions."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, LWWEntry]] = {}
        self._dirty: Dict[str, List[str]] = {}
        self._conflicts: List[ClockSkewConflict] = []

    def apply_remote(
        self,
        remote_entries: Dict[str, LWWEntry],
        branch_id: str,
    ) -> List[ClockSkewConflict]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        branch_store = self._store.setdefault(branch_id, {})
        for key, entry in remote_entries.items():
            branch_store[key] = entry
        return list(self._conflicts)

    def get_dirty_keys(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return self._dirty.get(branch_id, [])

    def checkpoint(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        keys = self._dirty.pop(branch_id, [])
        return keys

    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, LWWEntry]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return dict(self._store.get(branch_id, {}))
