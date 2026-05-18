"""Real implementation of AbstractL0SyncLayer using LWWMap and HybridTimestamp."""

from typing import Any, Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractL0SyncLayer
from chronopersona.memory_system.l0_crdt.hybrid_timestamp import HybridTimestamp
from chronopersona.memory_system.l0_crdt.lww_map import LWWEntry, LWWMap


class L0SyncLayer(AbstractL0SyncLayer):
    """L0 CRDT sync layer backed by LWWMap per branch."""

    def __init__(self, device_id: str) -> None:
        self.device_id: str = device_id
        self._maps: Dict[str, LWWMap] = {}

    def _get_map(self, branch_id: str) -> LWWMap:
        if branch_id not in self._maps:
            self._maps[branch_id] = LWWMap(device_id=self.device_id)
        return self._maps[branch_id]

    def get(self, key: str, branch_id: str) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        try:
            return lww.get(key)
        except KeyError:
            return None

    def set(self, key: str, value: Any, branch_id: str, device_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not device_id:
            raise ValueError("device_id must not be empty")
        lww = self._get_map(branch_id)
        ts = HybridTimestamp.now()
        lww.set(key, value, ts, device_id=device_id)

    def merge(self, remote_state: Dict[str, Any], branch_id: str) -> Dict[str, Any]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        remote_entries: Dict[str, LWWEntry] = {}
        for key, value in remote_state.items():
            if isinstance(value, LWWEntry):
                remote_entries[key] = value
            else:
                raise TypeError(
                    f"merge requires LWWEntry values, got {type(value).__name__} for key '{key}'"
                )
        conflicts = lww.merge(remote_entries)
        result: Dict[str, Any] = {}
        for c in conflicts:
            result[c.key] = {
                "local": c.local_entry.value,
                "remote": c.remote_entry.value,
            }
        return result

    def checkpoint(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        return lww.checkpoint()

    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        lww = self._get_map(branch_id)
        delta = lww.get_delta(since_vector_clock)
        return {k: v.value for k, v in delta.items()}
