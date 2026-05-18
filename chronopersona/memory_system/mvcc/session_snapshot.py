"""Session-MVCC snapshot writer (placeholder for Week 2)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from chronopersona.contracts.interfaces import AbstractVersionManager
from chronopersona.contracts.schemas import ChangeSet, Version


class SessionSnapshotWriter:
    """Writes session-level snapshots using the version manager.

    This is a placeholder implementation that delegates to
    AbstractVersionManager.commit().  In a full implementation it would
    serialise the LWWMap state and Qdrant metadata into a snapshot record.
    """

    def __init__(self, version_manager: AbstractVersionManager) -> None:
        self._version_manager = version_manager

    def write_snapshot(
        self,
        branch_id: str,
        session_id: str,
        lww_state: Dict[str, Any],
        qdrant_metadata: Optional[Dict[str, Any]] = None,
    ) -> Version:
        """Persist a session snapshot.

        Args:
            branch_id: Target branch.
            session_id: Session identifier.
            lww_state: Serialised LWWMap state.
            qdrant_metadata: Optional Qdrant collection metadata.

        Returns:
            The created Version record.
        """
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not session_id:
            raise ValueError("session_id must not be empty")

        changes = ChangeSet(
            entity_id=session_id,
            branch_id=branch_id,
            diff={"lww_state": lww_state, "qdrant_metadata": qdrant_metadata or {}},
        )
        return self._version_manager.commit(branch_id, changes)
