"""Unit tests for insight generator implementations."""

from typing import List

import pytest

from chronopersona.contracts.interfaces import IInsightGenerator
from chronopersona.contracts.schemas import Insight, MemoryEntry
from chronopersona.mocks.mock_insight_generator import MockInsightGenerator


class TestMockInsightGenerator:
    """Tests for MockInsightGenerator ensuring IInsightGenerator compliance."""

    def test_generate_returns_insights_for_memories(self) -> None:
        """T01: generate returns insights when memories are provided."""
        gen: IInsightGenerator = MockInsightGenerator()
        memories: List[MemoryEntry] = [
            MemoryEntry(id="m1", content="likes pizza"),
            MemoryEntry(id="m2", content="likes pasta"),
        ]
        insights = gen.generate("main", memories)
        assert len(insights) == 1
        assert isinstance(insights[0], Insight)
        assert insights[0].branch_id == "main"
        assert "m1" in insights[0].source_memory_ids

    def test_generate_returns_empty_for_empty_memories(self) -> None:
        """T02: generate returns empty list when no memories provided."""
        gen: IInsightGenerator = MockInsightGenerator()
        insights = gen.generate("main", [])
        assert insights == []

    def test_generate_empty_branch_raises_valueerror(self) -> None:
        """T03: generate with empty branch_id raises ValueError."""
        gen: IInsightGenerator = MockInsightGenerator()
        with pytest.raises(ValueError):
            gen.generate("", [MemoryEntry(content="x")])

    def test_should_trigger_true_at_threshold(self) -> None:
        """T04: should_trigger returns True when turn_count >= 10."""
        gen: IInsightGenerator = MockInsightGenerator()
        assert gen.should_trigger("main", 10) is True
        assert gen.should_trigger("main", 11) is True

    def test_should_trigger_false_below_threshold(self) -> None:
        """T05: should_trigger returns False when turn_count < 10."""
        gen: IInsightGenerator = MockInsightGenerator()
        assert gen.should_trigger("main", 9) is False
        assert gen.should_trigger("main", 0) is False
