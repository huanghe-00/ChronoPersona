"""[FUTURE] Memory migration service interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IMemoryMigrationService(ABC):
    """Cross-branch and cross-persona memory migration.

    W1: Interface frozen. Mock returns empty pass.
    W4+: Full implementation.
    """

    @abstractmethod
    def migrate(
        self,
        source: Any,
        target: Any,
        branch_id: str,
        filter_: Any,
    ) -> Any:
        """Migrate memories from source to target anchor.

        Args:
            source: Source MemoryAnchor.
            target: Target MemoryAnchor.
            branch_id: Execution branch. Must not be empty.
            filter_: MigrationFilter.

        Returns:
            MigrationResult.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def snapshot(self, branch_id: str) -> Any:
        """Create a snapshot of current branch state.

        Args:
            branch_id: Branch to snapshot. Must not be empty.

        Returns:
            Snapshot reference.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def merge_branches(self, source_branch: str, target_branch: str) -> Any:
        """Merge two branches.

        Args:
            source_branch: Source branch. Must not be empty.
            target_branch: Target branch. Must not be empty.

        Returns:
            MergeResult.

        Raises:
            ValueError: If any branch_id is empty.
        """
        ...
