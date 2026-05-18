"""Simple insight engine based on keyword statistics."""

from __future__ import annotations

import re
from typing import List

from chronopersona.contracts.interfaces import IInsightGenerator
from chronopersona.contracts.schemas import Insight, MemoryEntry


class SimpleInsightEngine(IInsightGenerator):
    """Lightweight insight generator using keyword co-occurrence.

    MVA implementation: detects simple patterns, trends, and conflicts
    from recent episodic memories without LLM calls.
    """

    _STOP_WORDS: set[str] = {
        "的", "了", "是", "我", "你", "在", "和", "就", "都", "要",
        "有", "这", "那", "个", "上", "下", "不", "也", "很", "到",
    }

    def generate(
        self,
        branch_id: str,
        recent_memories: List[MemoryEntry],
    ) -> List[Insight]:
        """Generate insights from recent memories."""
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not recent_memories:
            return []

        insights: List[Insight] = []
        contents = [m.content for m in recent_memories if m.content]

        # Pattern: frequent non-stop word appears >= 2 times
        word_counts: dict[str, int] = {}
        for content in contents:
            for word in self._extract_words(content):
                word_counts[word] = word_counts.get(word, 0) + 1

        for word, count in word_counts.items():
            if count >= 2 and len(word) >= 2:
                insights.append(
                    Insight(
                        id=f"insight-pattern-{word}",
                        insight_type="pattern",
                        source_memory_ids=[m.id for m in recent_memories[:3]],
                        content=f"User frequently mentions '{word}' ({count} times)",
                        confidence=min(0.5 + 0.1 * count, 0.95),
                        branch_id=branch_id,
                    )
                )
                break  # MVA: only top pattern

        # Conflict: simple antonym detection
        antonym_pairs = [("喜欢", "讨厌"), ("开心", "难过"), ("焦虑", "平静")]
        for pos, neg in antonym_pairs:
            pos_count = sum(1 for c in contents if pos in c)
            neg_count = sum(1 for c in contents if neg in c)
            if pos_count > 0 and neg_count > 0:
                insights.append(
                    Insight(
                        id="insight-conflict-001",
                        insight_type="conflict",
                        source_memory_ids=[m.id for m in recent_memories[:2]],
                        content=f"Detected conflicting sentiments: '{pos}' vs '{neg}'",
                        confidence=0.85,
                        branch_id=branch_id,
                    )
                )
                break

        # Trend: memory volume
        if len(recent_memories) >= 5:
            insights.append(
                Insight(
                    id="insight-trend-001",
                    insight_type="trend",
                    source_memory_ids=[m.id for m in recent_memories],
                    content=f"Conversation volume increased ({len(recent_memories)} recent memories)",
                    confidence=0.7,
                    branch_id=branch_id,
                )
            )

        return insights

    def should_trigger(self, branch_id: str, turn_count_since_last: int) -> bool:
        return turn_count_since_last >= 10

    def _extract_words(self, text: str) -> List[str]:
        """Extract candidate Chinese words using simple heuristic.

        Uses a sliding window of 2 characters over consecutive Chinese text.
        """
        chars = re.findall(r"[\u4e00-\u9fff]", text)
        result: list[str] = []
        for i in range(len(chars) - 1):
            word = chars[i] + chars[i + 1]
            if word not in self._STOP_WORDS:
                result.append(word)
        return result
