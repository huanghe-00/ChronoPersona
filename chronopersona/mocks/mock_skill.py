"""Mock skill implementing ISkill protocol."""

from typing import Any, Dict


class MockSkill:
    @property
    def skill_id(self) -> str:
        return "mock_skill"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A mock skill for testing."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {}

    def execute(self, params: Dict[str, Any], branch_id: str, persona_id: str) -> Dict[str, str]:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return {"result": "mock"}
