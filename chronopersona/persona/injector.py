"""Lightweight PersonaInjector implementation."""

from typing import Any

from loguru import logger

from chronopersona.contracts.interfaces import IPersonaInjector


class PersonaInjector(IPersonaInjector):
    """Dictionary-based persona injection/ejection.

    MVA: Only handles static attribute injection into context dictionary.
    Dynamic state and identity anchor are [FUTURE].
    """

    def inject(self, persona_id: str, branch_id: str, target: Any) -> None:
        """Inject persona static attributes into target context.

        Args:
            persona_id: Persona to activate.
            branch_id: Target branch.
            target: Mutable context object (must support dict-like update).

        Raises:
            ValueError: If persona_id or branch_id is empty.
        """
        if not persona_id or not branch_id:
            raise ValueError("persona_id and branch_id must not be empty")
        logger.info(
            "PersonaInjector: injecting {} into branch {}", persona_id, branch_id
        )
        if hasattr(target, "update"):
            target.update({"persona_id": persona_id, "branch_id": branch_id})

    def eject(self, persona_id: str, branch_id: str) -> None:
        """Eject persona from target context.

        MVA: No-op, real cleanup is [FUTURE].
        """
        if not persona_id or not branch_id:
            raise ValueError("persona_id and branch_id must not be empty")
        logger.info(
            "PersonaInjector: ejecting {} from branch {}", persona_id, branch_id
        )
