"""Unit tests for PersonaInjector."""

from unittest.mock import MagicMock

import pytest

from chronopersona.contracts.interfaces import IPersonaInjector
from chronopersona.persona.injector import PersonaInjector


class TestPersonaInjector:
    """Tests for lightweight PersonaInjector."""

    def test_inject_updates_context(self) -> None:
        """T01: inject updates target context with persona_id."""
        injector: IPersonaInjector = PersonaInjector()
        ctx: dict[str, str] = {}
        injector.inject("therapist", "main", ctx)
        assert ctx["persona_id"] == "therapist"
        assert ctx["branch_id"] == "main"

    def test_inject_empty_persona_raises_valueerror(self) -> None:
        """T02: inject with empty persona_id raises ValueError."""
        injector: IPersonaInjector = PersonaInjector()
        with pytest.raises(ValueError):
            injector.inject("", "main", {})

    def test_inject_empty_branch_raises_valueerror(self) -> None:
        """T03: inject with empty branch_id raises ValueError."""
        injector: IPersonaInjector = PersonaInjector()
        with pytest.raises(ValueError):
            injector.inject("therapist", "", {})

    def test_eject_empty_persona_raises_valueerror(self) -> None:
        """T04: eject with empty persona_id raises ValueError."""
        injector: IPersonaInjector = PersonaInjector()
        with pytest.raises(ValueError):
            injector.eject("", "main")

    def test_eject_empty_branch_raises_valueerror(self) -> None:
        """T05: eject with empty branch_id raises ValueError."""
        injector: IPersonaInjector = PersonaInjector()
        with pytest.raises(ValueError):
            injector.eject("therapist", "")

    def test_inject_on_magicmock(self) -> None:
        """T06: inject works on MagicMock (has update)."""
        injector: IPersonaInjector = PersonaInjector()
        target = MagicMock()
        injector.inject("rpg-hero", "branch-a", target)
        target.update.assert_called_once_with(
            {"persona_id": "rpg-hero", "branch_id": "branch-a"}
        )
