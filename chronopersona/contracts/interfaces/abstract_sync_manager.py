"""Abstract interface for sync manager bridging L0 CRDT and L3 version storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class AbstractSyncManager(ABC):
    """Bridge L0 CRDT dirty state to persistent version snapshots.

    Implementations must coordinate with AbstractL0SyncLayer for dirty key
    retrieval and AbstractVersionManager for snapshot commit.
    All operations require an explicit branch_id.
    """

    @abstractmethod
    def checkpoint(self, branch_id: str) -> List[str]:
        """Flush pending dirty keys for branch and commit a version snapshot.

        Args:
            branch_id: Explicit target branch identifier.

        Returns:
            List of dirty keys that were flushed.

        Raises:
            ValueError: If branch_id is empty.
        """
