"""Abstract L0 CRDT synchronization interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AbstractL0SyncLayer(ABC):
    """Abstract interface for L0 LWW-CRDT distributed synchronization.

    Replaces Yjs in the original design. Implementations must support
    multi-device add-wins semantics using Hybrid Logical Clocks (HLC).
    All operations require an explicit branch_id.
    """

    @abstractmethod
    def get(self, key: str, branch_id: str) -> Any:
        """Retrieve the current value for a key in the LWWMap.

        Args:
            key: The key to look up.
            branch_id: Branch context. Must not be empty.

        Returns:
            The latest value according to LWW semantics.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        branch_id: str,
        device_id: str,
    ) -> None:
        """Set a value in the LWWMap, broadcasting to peers.

        Args:
            key: The key to set.
            value: The value to store.
            branch_id: Branch context. Must not be empty.
            device_id: Originating device identifier. Must not be empty.

        Raises:
            ValueError: If branch_id or device_id is empty.
        """
        ...

    @abstractmethod
    def merge(self, remote_state: Dict[str, Any], branch_id: str) -> Dict[str, Any]:
        """Merge a remote LWWMap state into the local state.

        Args:
            remote_state: Serialized remote LWWMap state.
            branch_id: Branch context. Must not be empty.

        Returns:
            Conflict report: keys where both sides had concurrent writes.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def checkpoint(self, branch_id: str) -> List[str]:
        """Flush dirty keys to L3 and return checkpointed keys.

        Args:
            branch_id: Branch to checkpoint. Must not be empty.

        Returns:
            List of keys that were flushed.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Compute delta since a given vector clock for incremental sync.

        Args:
            branch_id: Branch to query. Must not be empty.
            since_vector_clock: Optional vector clock baseline. None = full state.

        Returns:
            Serialized delta state.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
