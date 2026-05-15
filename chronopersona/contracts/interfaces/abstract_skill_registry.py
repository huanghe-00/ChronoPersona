"""[FUTURE] Skill registry interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List


class ISkillRegistry(ABC):
    """Skill lifecycle management.

    W1: Interface frozen. Mock returns empty pass.
    W4+: Full implementation.
    """

    @abstractmethod
    def register(self, skill: Any, branch_id: str) -> None:
        """Register a skill to a branch.

        Args:
            skill: Skill instance.
            branch_id: Target branch. Must not be empty.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...

    @abstractmethod
    def execute(self, skill_id: str, params: Any, branch_id: str) -> Any:
        """Execute a skill by ID.

        Args:
            skill_id: Skill identifier.
            params: Execution parameters.
            branch_id: Branch context. Must not be empty.

        Returns:
            SkillResult.

        Raises:
            ValueError: If branch_id or skill_id is empty.
        """
        ...

    @abstractmethod
    def get_available_skills(self, branch_id: str, persona_id: str) -> List[Any]:
        """List skills available to a persona on a branch.

        Args:
            branch_id: Branch scope. Must not be empty.
            persona_id: Persona identifier.

        Returns:
            List of skill instances.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
