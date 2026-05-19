"""Concrete implementation of AbstractSyncManager backed by LWWMap."""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from chronopersona.contracts.interfaces.abstract_sync_manager import AbstractSyncManager
from chronopersona.memory_system.l0_crdt.lww_map import ClockSkewConflict, LWWEntry, LWWMap


class SyncManager(AbstractSyncManager):
    """Per-branch LWWMap manager that implements AbstractSyncManager."""

    def __init__(self, device_id: str) -> None:
        self._device_id = device_id
        self._maps: Dict[str, LWWMap] = {}

    def _get_map(self, branch_id: str) -> LWWMap:
        if branch_id not in self._maps:
            self._maps[branch_id] = LWWMap(device_id=self._device_id)
        return self._maps[branch_id]

    def apply_remote(
        self,
        remote_entries: Dict[str, LWWEntry],
        branch_id: str,
    ) -> List[ClockSkewConflict]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        conflicts = lww.merge(remote_entries)
        logger.info(
            "Applied {} remote entries to branch '{}', {} conflicts",
            len(remote_entries),
            branch_id,
            len(conflicts),
        )
        return conflicts

    def get_dirty_keys(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        return list(lww._dirty_keys)

    def checkpoint(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        keys = lww.checkpoint()
        logger.info("Checkpoint for branch '{}': {} keys", branch_id, len(keys))
        return keys

    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, LWWEntry]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        return lww.get_delta(since_vector_clock)
