"""Mock implementation of IPersonaInjector."""

from typing import Any

from chronopersona.contracts.interfaces import IPersonaInjector


class MockPersonaInjector(IPersonaInjector):
    def inject(self, persona_id: str, branch_id: str, target: Any) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")

    def eject(self, persona_id: str, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
