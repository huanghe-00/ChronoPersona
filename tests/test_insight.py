"""Tests for InsightGenerator interface and Mock."""

import pytest

from chronopersona.contracts.schemas import Insight, MemoryEntry
from chronopersona.mocks import MockInsightGenerator


class TestMockInsightGenerator:
    """Tests for MockInsightGenerator."""

    def test_generate_empty_memories_returns_empty(self) -> None:
        """No memories yields no insights."""
        gen = MockInsightGenerator()
        assert gen.generate("main", []) == []

    def test_generate_returns_insights(self) -> None:
        """With memories, returns mock insights."""
        gen = MockInsightGenerator()
        memories = [
            MemoryEntry(content="I like Sichuan food"),
            MemoryEntry(content="I enjoy spicy dishes"),
        ]
        insights = gen.generate("main", memories)
        assert len(insights) == 1
        assert insights[0].insight_type == "pattern"
        assert insights[0].branch_id == "main"

    def test_generate_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        gen = MockInsightGenerator()
        with pytest.raises(ValueError):
            gen.generate("", [MemoryEntry(content="test")])

    def test_should_trigger_at_threshold(self) -> None:
        """Trigger fires at turn_count >= 10."""
        gen = MockInsightGenerator()
        assert gen.should_trigger("main", 9) is False
        assert gen.should_trigger("main", 10) is True
        assert gen.should_trigger("main", 15) is True

    def test_insight_schema_fields(self) -> None:
        """Insight dataclass carries expected fields."""
        ins = Insight(
            id="i1",
            insight_type="trend",
            source_memory_ids=["m1", "m2"],
            content="Anxiety level rising",
            confidence=0.75,
        )
        assert ins.confidence == 0.75
        assert ins.valid_until is None
