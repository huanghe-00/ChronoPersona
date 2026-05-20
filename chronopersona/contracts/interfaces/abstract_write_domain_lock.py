"""Abstract interface for write-domain locking."""

from abc import ABC, abstractmethod
from typing import Optional


class AbstractWriteDomainLock(ABC):
    """Explicitly define conflict-free write domains.

    Ensures that the same entity is not concurrently modified
    across devices or agents.
    """

    @abstractmethod
    def acquire(self, layer: str, entity_id: str, branch_id: str) -> bool:
        """Attempt to acquire a write lock for the given entity.

        Args:
            layer: Memory layer identifier (L0, L1, L2, L3).
            entity_id: Unique identifier of the entity.
            branch_id: Branch context for the lock.

        Returns:
            True if the lock was acquired, False otherwise.
        """
        ...

    @abstractmethod
    def release(self, layer: str, entity_id: str, branch_id: str) -> None:
        """Release a previously acquired write lock.

        Args:
            layer: Memory layer identifier.
            entity_id: Unique identifier of the entity.
            branch_id: Branch context for the lock.
        """
        ...

    @abstractmethod
    def is_locked(self, layer: str, entity_id: str, branch_id: str) -> bool:
        """Check whether a write lock is currently held.

        Args:
            layer: Memory layer identifier.
            entity_id: Unique identifier of the entity.
            branch_id: Branch context for the lock.

        Returns:
            True if the entity is locked, False otherwise.
        """
        ...
