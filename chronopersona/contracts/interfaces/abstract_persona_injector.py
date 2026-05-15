"""[FUTURE] Persona injection interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IPersonaInjector(ABC):
    """Persona context injection and ejection.

    W1: Interface frozen. Mock returns empty pass.
    W4+: Full implementation.
    """

    @abstractmethod
    def inject(self, persona_id: str, branch_id: str, target: Any) -> None:
        """Inject persona context into target context.

        Args:
            persona_id: Persona to inject.
            branch_id: Target branch. Must not be empty.
            target: Context object to receive injection.

        Raises:
            ValueError: If any required argument is empty.
        """
        ...

    @abstractmethod
    def eject(self, persona_id: str, branch_id: str) -> None:
        """Remove persona context from target branch.

        Args:
            persona_id: Persona to eject.
            branch_id: Target branch. Must not be empty.

        Raises:
            ValueError: If any required argument is empty.
        """
        ...
