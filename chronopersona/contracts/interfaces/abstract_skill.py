"""[FUTURE] Skill protocol."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ISkill(Protocol):
    """Skill protocol defining executable capability primitives.

    W1: Protocol frozen. Mock returns empty pass.
    W4+: Full implementation.
    """

    @property
    def skill_id(self) -> str:
        """Global unique skill identifier."""
        ...

    @property
    def version(self) -> str:
        """Semantic version string."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description for LLM tool exposure."""
        ...

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema for parameter validation."""
        ...

    def execute(self, params: Dict[str, Any], branch_id: str, persona_id: str) -> Any:
        """Execute the skill.

        Args:
            params: Model-generated parameters.
            branch_id: Explicit branch context. Must not be empty.
            persona_id: Current persona for execution.

        Returns:
            SkillResult.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
