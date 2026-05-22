"""Unit tests for L1 Working Memory sliding window (Week 2 Day 2)."""

from typing import List

import pytest

from chronopersona.memory_system.l1_working import (
    CompressedSummary,
    TurnEntry,
    WorkingMemoryWindow,
)


class TestTurnEntry:
    """T38: Turn token estimation."""

    def test_token_estimation_mixed(self) -> None:
        """T38: Mixed Chinese and English token counting."""
        turn = TurnEntry(1, "你好 world", "OK 明白")
        assert turn.token_count == 6


class TestWorkingMemoryWindow:
    """T39-T42: L1 sliding window and compression."""

    def test_add_turn_and_get_context_order(self) -> None:
        """T39: Context returns newest-first order."""
        l1 = WorkingMemoryWindow(branch_id="main", session_id="s1", max_turns=100)
        l1.add_turn("hello", "hi", branch_id="main")
        l1.add_turn("how are you", "fine", branch_id="main")
        ctx = l1.get_context(branch_id="main")
        assert len(ctx) == 2
        assert isinstance(ctx[0], TurnEntry)
        assert ctx[0].turn_id == 2
        assert ctx[1].turn_id == 1

    def test_max_turns_compression(self) -> None:
        """T40: Exceeding max_turns triggers compression."""
        l1 = WorkingMemoryWindow(branch_id="main", session_id="s1", max_turns=3)
        for i in range(5):
            l1.add_turn(f"msg{i}", f"reply{i}", branch_id="main")
        assert len(l1._turns) <= 3
        assert len(l1._compressed_summaries) > 0
        turn_ids = {t.turn_id for t in l1._turns}
        assert 1 not in turn_ids
        assert 2 not in turn_ids

    def test_token_threshold_compression(self) -> None:
        """T41: Exceeding token threshold triggers compression."""
        big_text = "你好 " * 500
        l1 = WorkingMemoryWindow(
            branch_id="main",
            session_id="s1",
            max_turns=100,
            token_threshold=500,
        )
        l1.add_turn(big_text, "reply1", branch_id="main")
        l1.add_turn(big_text, "reply2", branch_id="main")
        assert l1.total_tokens <= l1.token_threshold
        assert len(l1._compressed_summaries) > 0

    def test_custom_compressor(self) -> None:
        """T42: Custom compressor is invoked and its output retained."""
        calls: List[List[int]] = []

        def mock_compressor(turns: List[TurnEntry]) -> str:
            calls.append([t.turn_id for t in turns])
            return f"MockSummary:{len(turns)}"

        l1 = WorkingMemoryWindow(
            branch_id="main",
            session_id="s1",
            max_turns=2,
            compressor=mock_compressor,
        )
        l1.add_turn("a", "b", branch_id="main")
        l1.add_turn("c", "d", branch_id="main")
        l1.add_turn("e", "f", branch_id="main")
        assert len(calls) > 0
        assert any("MockSummary" in s.content for s in l1._compressed_summaries)
