"""Tests for SimpleInsightEngine."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.memory_system.insight.simple_insight_engine import SimpleInsightEngine


class TestSimpleInsightEngine:
    """Tests for lightweight insight generation."""

    def test_generate_empty_memories(self) -> None:
        """No memories yields no insights."""
        engine = SimpleInsightEngine()
        assert engine.generate("main", []) == []

    def test_generate_detects_pattern(self) -> None:
        """Repeated keyword generates pattern insight."""
        engine = SimpleInsightEngine()
        memories = [
            MemoryEntry(content="我喜欢川菜"),
            MemoryEntry(content="川菜真的很棒"),
            MemoryEntry(content="昨天去了川菜馆"),
        ]
        insights = engine.generate("main", memories)
        assert any(i.insight_type == "pattern" for i in insights)
        assert any("川菜" in i.content for i in insights)

    def test_generate_detects_conflict(self) -> None:
        """Opposite sentiments generate conflict insight."""
        engine = SimpleInsightEngine()
        memories = [
            MemoryEntry(content="我喜欢工作"),
            MemoryEntry(content="我讨厌工作"),
        ]
        insights = engine.generate("main", memories)
        assert any(i.insight_type == "conflict" for i in insights)

    def test_generate_trend_with_volume(self) -> None:
        """Many memories generate trend insight."""
        engine = SimpleInsightEngine()
        memories = [MemoryEntry(content=f"turn {i}") for i in range(5)]
        insights = engine.generate("main", memories)
        assert any(i.insight_type == "trend" for i in insights)

    def test_generate_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        engine = SimpleInsightEngine()
        with pytest.raises(ValueError):
            engine.generate("", [MemoryEntry(content="test")])

    def test_should_trigger_at_threshold(self) -> None:
        """Trigger fires at turn_count >= 10."""
        engine = SimpleInsightEngine()
        assert engine.should_trigger("main", 9) is False
        assert engine.should_trigger("main", 10) is True

    def test_jieba_segmentation_chinese(self) -> None:
        """jieba correctly segments Chinese phrases into real words."""
        engine = SimpleInsightEngine()
        words = engine._extract_words("我喜欢川菜和Python编程")
        assert "川菜" in words
        assert "Python" in words
        assert "编程" in words
        assert "喜欢" in words
        # Pseudo-words like '欢川' must not appear
        assert not any("欢川" in w for w in words)

    def test_jieba_filters_stopwords(self) -> None:
        """Stop words are removed after jieba segmentation."""
        engine = SimpleInsightEngine()
        words = engine._extract_words("我和我的祖国")
        assert "祖国" in words
        assert "我" not in words
        assert "和" not in words
