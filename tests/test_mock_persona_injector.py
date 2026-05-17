"""Unit tests for MockPersonaInjector."""

import pytest

from chronopersona.mocks import MockPersonaInjector


class TestMockPersonaInjector:
    """Tests for MockPersonaInjector (W1 frozen mock)."""

    def test_inject_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on inject."""
        injector = MockPersonaInjector()
        with pytest.raises(ValueError):
            injector.inject(persona_id="p1", branch_id="", target=None)

    def test_eject_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError on eject."""
        injector = MockPersonaInjector()
        with pytest.raises(ValueError):
            injector.eject(persona_id="p1", branch_id="")

    def test_inject_eject_no_exception(self) -> None:
        """Normal inject/eject does not raise."""
        injector = MockPersonaInjector()
        injector.inject(persona_id="p1", branch_id="main", target=None)
        injector.eject(persona_id="p1", branch_id="main")
