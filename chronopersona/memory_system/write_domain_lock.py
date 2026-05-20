"""In-memory write-domain lock implementation."""

from typing import Dict, Set, Tuple

from chronopersona.contracts.interfaces.abstract_write_domain_lock import (
    AbstractWriteDomainLock,
)


class WriteDomainLock(AbstractWriteDomainLock):
    """Simple in-memory lock manager for write domains.

    Locks are identified by (layer, entity_id, branch_id).
    """

    def __init__(self) -> None:
        self._locks: Dict[Tuple[str, str, str], bool] = {}

    def acquire(self, layer: str, entity_id: str, branch_id: str) -> bool:
        key = (layer, entity_id, branch_id)
        if key in self._locks:
            return False
        self._locks[key] = True
        return True

    def release(self, layer: str, entity_id: str, branch_id: str) -> None:
        key = (layer, entity_id, branch_id)
        self._locks.pop(key, None)

    def is_locked(self, layer: str, entity_id: str, branch_id: str) -> bool:
        key = (layer, entity_id, branch_id)
        return key in self._locks
