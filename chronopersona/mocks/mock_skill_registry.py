"""Mock implementation of ISkillRegistry."""

from typing import Any, List

from chronopersona.contracts.interfaces import ISkillRegistry


class MockSkillRegistry(ISkillRegistry):
    def register(self, skill: Any, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

    def execute(self, skill_id: str, params: Any, branch_id: str) -> Any:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return {"status": "mock_executed"}

    def get_available_skills(self, branch_id: str, persona_id: str) -> List[Any]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return []
