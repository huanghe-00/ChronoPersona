"""Abstract interface for the L0 sync manager."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from chronopersona.memory_system.l0_crdt.lww_map import ClockSkewConflict, LWWEntry


class AbstractSyncManager(ABC):
    """Manages L0 CRDT state synchronisation across devices.

    Responsibilities:
    - Accept remote LWW entries and merge them into the local LWWMap.
    - Expose dirty keys for checkpointing.
    - Provide delta state for incremental sync.
    - Track clock-skew conflicts for upstream CONTRADICTS edge creation.
    """

    @abstractmethod
    def apply_remote(
        self,
        remote_entries: Dict[str, LWWEntry],
        branch_id: str,
    ) -> List[ClockSkewConflict]:
        """Merge remote entries into the local LWWMap for *branch_id*.

        Args:
            remote_entries: Key → LWWEntry mapping received from a peer.
            branch_id: Explicit branch identifier.

        Returns:
            List of clock-skew conflicts detected during merge.
        """
        ...

    @abstractmethod
    def get_dirty_keys(self, branch_id: str) -> List[str]:
        """Return keys that have been modified since the last checkpoint.

        Args:
            branch_id: Explicit branch identifier.

        Returns:
            List of dirty key names.
        """
        ...

    @abstractmethod
    def checkpoint(self, branch_id: str) -> List[str]:
        """Persist dirty keys and clear the dirty set.

        Args:
            branch_id: Explicit branch identifier.

        Returns:
            Snapshot of keys that were persisted.
        """
        ...

    @abstractmethod
    def get_delta(
        self,
        branch_id: str,
        since_vector_clock: Optional[Dict[str, int]] = None,
    ) -> Dict[str, LWWEntry]:
        """Return entries newer than *since_vector_clock*.

        Args:
            branch_id: Explicit branch identifier.
            since_vector_clock: Per-device logical timestamps. If None,
                return all entries.

        Returns:
            Key → LWWEntry mapping for entries that are newer.
        """
        ...
