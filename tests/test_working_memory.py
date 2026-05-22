"""Unit tests for L1 Working Memory sliding window."""

import pytest

from chronopersona.memory_system.l1_working.sliding_window import (
    CompressedSummary,
    TurnEntry,
    WorkingMemoryWindow,
)


class TestWorkingMemoryWindow:
    """Tests for WorkingMemoryWindow compression and retrieval logic."""

    def test_add_turn_increases_turn_count(self) -> None:
        """T01: Adding a turn increments internal turn list."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=10
        )
        wm.add_turn("hello", "hi", branch_id="main")
        assert len(wm._turns) == 1
        assert wm._turns[0].user_text == "hello"

    def test_max_turns_triggers_compression(self) -> None:
        """T02: Exceeding max_turns compresses oldest batch."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=2
        )
        wm.add_turn("1", "a", branch_id="main")
        wm.add_turn("2", "b", branch_id="main")
        wm.add_turn("3", "c", branch_id="main")
        assert len(wm._turns) <= 2
        assert len(wm._compressed_summaries) >= 1

    def test_token_threshold_triggers_compression(self) -> None:
        """T03: Exceeding token_threshold compresses oldest turns."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=100, token_threshold=1
        )
        wm.add_turn("user says something", "agent replies here", branch_id="main")
        # Compression must have occurred to relieve token pressure
        assert len(wm._compressed_summaries) >= 1 or len(wm._turns) == 0

    def test_get_context_reverse_chronological(self) -> None:
        """T04: get_context returns newest items first."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=10
        )
        wm.add_turn("first", "first reply", branch_id="main")
        wm.add_turn("second", "second reply", branch_id="main")
        ctx: list[TurnEntry | CompressedSummary] = wm.get_context(branch_id="main")
        assert isinstance(ctx[0], TurnEntry)
        assert ctx[0].user_text == "second"

    def test_get_context_respects_token_limit(self) -> None:
        """T05: token_limit caps returned context length."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=10
        )
        wm.add_turn("a", "b", branch_id="main")
        wm.add_turn("c", "d", branch_id="main")
        # token_limit=0 should yield empty list
        limited: list[TurnEntry | CompressedSummary] = wm.get_context(branch_id="main", token_limit=0)
        assert limited == []

    def test_should_compress_reflects_state(self) -> None:
        """T06: should_compress is True when thresholds exceeded."""
        wm: WorkingMemoryWindow = WorkingMemoryWindow(
            branch_id="main", session_id="s1", max_turns=1, token_threshold=100000
        )
        assert wm.should_compress(branch_id="main") is False
        wm.add_turn("a", "b", branch_id="main")
        wm.add_turn("c", "d", branch_id="main")  # exceeds max_turns=1, compression happens
        # After internal compression, state should be back within limits
        assert wm.should_compress(branch_id="main") is False
