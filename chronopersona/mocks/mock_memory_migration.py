"""Mock implementation of IMemoryMigrationService."""

from typing import Any

from chronopersona.contracts.interfaces import IMemoryMigrationService


class MockMemoryMigrationService(IMemoryMigrationService):
    def migrate(
        self,
        source: Any,
        target: Any,
        branch_id: str,
        filter_: Any,
    ) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return {"migrated_count": 0}

    def snapshot(self, branch_id: str) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return {}

    def merge_branches(self, source_branch: str, target_branch: str) -> Any:
        if not source_branch or not target_branch:
            raise ValueError("branch_ids must not be empty")
        return {"merged": True}
