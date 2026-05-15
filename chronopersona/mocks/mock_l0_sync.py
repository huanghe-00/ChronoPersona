"""Mock implementation of AbstractL0SyncLayer."""

from typing import Any, Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractL0SyncLayer


class MockL0SyncLayer(AbstractL0SyncLayer):
    """Mock LWW-CRDT sync layer for testing."""

    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, Any]] = {}  # branch_id -> {key: value}
        self._clocks: Dict[str, Dict[str, int]] = {}  # branch_id -> vector_clock

    def get(self, key: str, branch_id: str) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return self._state.get(branch_id, {}).get(key)

    def set(
        self,
        key: str,
        value: Any,
        branch_id: str,
        device_id: str,
    ) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not device_id:
            raise ValueError("device_id must not be empty")
        self._state.setdefault(branch_id, {})[key] = value
        self._clocks.setdefault(branch_id, {})[device_id] = (
            self._clocks.get(branch_id, {}).get(device_id, 0) + 1
        )

    def merge(self, remote_state: Dict[str, Any], branch_id: str) -> Dict[str, Any]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        local = self._state.get(branch_id, {})
        conflicts: Dict[str, Any] = {}
        for key, value in remote_state.items():
            if key in local and local[key] != value:
                conflicts[key] = {"local": local[key], "remote": value}
            self._state.setdefault(branch_id, {})[key] = value
        return conflicts

    def checkpoint(self, branch_id: str) -> List[str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return list(self._state.get(branch_id, {}).keys())

    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return dict(self._state.get(branch_id, {}))
