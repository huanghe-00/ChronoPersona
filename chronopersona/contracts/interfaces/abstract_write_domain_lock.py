"""Abstract interface for write domain lock."""

from abc import ABC, abstractmethod


class IWriteDomainLock(ABC):
    """Write domain lock ensuring no concurrent writes to the same entity.

    Inspired by structured-data domain best practices: physical isolation
    is preferred over automatic merging for semantic-level data.
    """

    @abstractmethod
    def acquire(self, layer: str, entity_id: str, branch_id: str) -> bool:
        """Attempt to acquire write lock for entity.

        Args:
            layer: Memory layer (L0, L1, L2, or L3).
            entity_id: Unique entity identifier within the layer.
            branch_id: Explicit branch for isolation.

        Returns:
            True if lock acquired, False if already held.

        Raises:
            ValueError: If layer, entity_id, or branch_id is empty.
        """

    @abstractmethod
    def release(self, layer: str, entity_id: str, branch_id: str) -> None:
        """Release write lock for entity."""

    @abstractmethod
    def is_locked(self, layer: str, entity_id: str, branch_id: str) -> bool:
        """Check if entity is currently locked."""
