"""Abstract MVCC Version Manager interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from chronopersona.contracts.schemas.version import ChangeSet, MergeResult, Snapshot, Version


class AbstractVersionManager(ABC):
    """Abstract interface for MVCC version and branch management.

    Implementations must support both L2 Session-MVCC (coarse-grained)
    and L3 Entity-MVCC (fine-grained). All operations require an explicit
    branch_id; default global branch is strictly prohibited.
    """

    @abstractmethod
    def commit(self, branch_id: str, changes: ChangeSet) -> Version:
        """Create a new version by committing changes to a branch.

        Args:
            branch_id: Target branch identifier. Must not be empty.
            changes: Structured change set describing the delta.

        Returns:
            Version metadata including timestamp and vector clock.

        Raises:
            ValueError: If branch_id is empty or changes are invalid.
            RuntimeError: If the underlying storage operation fails.
        """
        ...

    @abstractmethod
    def checkout(
        self,
        branch_id: str,
        version: Optional[str] = None,
    ) -> Snapshot:
        """Checkout a branch state, optionally at a specific version.

        Args:
            branch_id: Branch to checkout. Must not be empty.
            version: Optional version hash. If None, checks out latest.

        Returns:
            Snapshot containing the full branch state at that version.

        Raises:
            ValueError: If branch_id is empty.
            LookupError: If branch or version does not exist.
        """
        ...

    @abstractmethod
    def merge(self, source_branch: str, target_branch: str) -> MergeResult:
        """Merge source branch into target branch.

        Args:
            source_branch: Source branch identifier. Must not be empty.
            target_branch: Target branch identifier. Must not be empty.

        Returns:
            MergeResult containing conflicts and resolution statistics.

        Raises:
            ValueError: If any branch_id is empty or branches are identical.
            RuntimeError: If merge cannot be completed automatically.
        """
        ...

    @abstractmethod
    def log(
        self,
        branch_id: str,
        entity_id: Optional[str] = None,
    ) -> List[Version]:
        """Retrieve version history for a branch or specific entity.

        Args:
            branch_id: Branch to query. Must not be empty.
            entity_id: Optional entity to filter history. None means branch-level.

        Returns:
            Chronological list of versions, newest last.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def gc(self, branch_id: str, keep_last_n: int = 10) -> int:
        """Garbage collect old versions, retaining the most recent N.

        Args:
            branch_id: Branch to clean up. Must not be empty.
            keep_last_n: Number of recent versions to preserve. Must be >= 1.

        Returns:
            Number of versions deleted.

        Raises:
            ValueError: If branch_id is empty or keep_last_n < 1.
        """
        ...
