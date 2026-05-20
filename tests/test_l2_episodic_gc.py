"""Unit tests for L2EpisodicGC."""

import pytest

from chronopersona.memory_system.l2_episodic.gc import L2EpisodicGC


class TestL2EpisodicGC:
    """Tests for exponential decay garbage collector."""

    def test_collect_empty_branch_raises_valueerror(self) -> None:
        """T01: collect with empty branch_id raises ValueError."""
        gc = L2EpisodicGC()
        with pytest.raises(ValueError):
            gc.collect(None, "")

    def test_collect_returns_int(self) -> None:
        """T02: collect returns integer count of removed entries."""
        gc = L2EpisodicGC()
        removed = gc.collect(None, "main")
        assert isinstance(removed, int)
        assert removed == 0

    def test_ttl_base_default(self) -> None:
        """T03: default ttl_base is 24.0 hours."""
        gc = L2EpisodicGC()
        assert gc._ttl_base == 24.0

    def test_custom_ttl_base(self) -> None:
        """T04: custom ttl_base is accepted."""
        gc = L2EpisodicGC(ttl_base=48.0)
        assert gc._ttl_base == 48.0
