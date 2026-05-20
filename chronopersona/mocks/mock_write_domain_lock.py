"""Mock implementation of AbstractWriteDomainLock for testing."""

from typing import Dict, Set, Tuple

from chronopersona.contracts.interfaces.abstract_write_domain_lock import (
    IWriteDomainLock,
)


class MockWriteDomainLock(IWriteDomainLock):
    """Mock write-domain lock that always succeeds.

    Useful for tests that do not need real locking semantics.
    """

    def __init__(self) -> None:
        self._acquired: Set[Tuple[str, str, str]] = set()

    def acquire(self, layer: str, entity_id: str, branch_id: str) -> bool:
        self._acquired.add((layer, entity_id, branch_id))
        return True

    def release(self, layer: str, entity_id: str, branch_id: str) -> None:
        self._acquired.discard((layer, entity_id, branch_id))

    def is_locked(self, layer: str, entity_id: str, branch_id: str) -> bool:
        return (layer, entity_id, branch_id) in self._acquired
