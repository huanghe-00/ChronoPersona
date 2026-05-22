"""Mock implementation of AbstractVersionManager."""

from typing import Dict, List, Optional

from chronopersona.contracts.interfaces import AbstractVersionManager
from chronopersona.contracts.schemas import ChangeSet, MergeResult, Snapshot, Version


class MockVersionManager(AbstractVersionManager):
    """Mock version manager for testing."""

    def __init__(self) -> None:
        self._versions: Dict[str, List[Version]] = {}
        self._counter = 0

    @property
    def versions(self) -> List[Version]:
        """Return a flat list of all committed versions across branches."""
        result: List[Version] = []
        for branch_list in self._versions.values():
            result.extend(branch_list)
        return result

    def _next_version(self, branch_id: str) -> str:
        self._counter += 1
        return f"{branch_id}-v{self._counter}"

    def commit(self, branch_id: str, changes: ChangeSet) -> Version:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        v = Version(branch_id=branch_id, version=self._next_version(branch_id))
        self._versions.setdefault(branch_id, []).append(v)
        return v

    def checkout(
        self,
        branch_id: str,
        version: Optional[str] = None,
    ) -> Snapshot:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return Snapshot(branch_id=branch_id, version=version)

    def merge(self, source_branch: str, target_branch: str) -> MergeResult:
        if not source_branch or not target_branch:
            raise ValueError("branch_ids must not be empty")
        return MergeResult(source_branch=source_branch, target_branch=target_branch)

    def log(
        self,
        branch_id: str,
        entity_id: Optional[str] = None,
    ) -> List[Version]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return list(self._versions.get(branch_id, []))

    def gc(self, branch_id: str, keep_last_n: int = 10) -> int:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if keep_last_n < 1:
            raise ValueError("keep_last_n must be >= 1")
        versions = self._versions.get(branch_id, [])
        if len(versions) > keep_last_n:
            removed = len(versions) - keep_last_n
            self._versions[branch_id] = versions[-keep_last_n:]
            return removed
        return 0
