"""Tests for ConditionalDistiller."""

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.memory_system.insight.conditional_distiller import ConditionalDistiller


class TestConditionalDistiller:
    """MVA conditional rule extraction tests."""

    def setup_method(self):
        self.distiller = ConditionalDistiller(min_confidence=0.7)

    def test_distill_if_then_rule(self):
        """T1: Extract 如果...就... rule."""
        mem = MemoryEntry(
            id="mem-001",
            content="如果用户提到性能优化，就应该主动建议查看火焰图",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 1
        assert "性能优化" in rules[0].trigger
        assert "火焰图" in rules[0].action
        assert rules[0].confidence >= 0.7
        assert rules[0].negation_preserved is False

    def test_distill_when_rule(self):
        """T2: Extract 当...时... rule."""
        mem = MemoryEntry(
            id="mem-002",
            content="当用户焦虑时，应该降低语速并表达共情",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 1
        assert "用户焦虑" in rules[0].trigger
        assert "降低语速" in rules[0].action

    def test_negation_preservation(self):
        """T3: Negation words in trigger are preserved and flagged."""
        mem = MemoryEntry(
            id="mem-003",
            content="如果用户没有明确拒绝，就不要停止当前任务",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 1
        assert "没有明确拒绝" in rules[0].trigger
        assert rules[0].negation_preserved is True

    def test_no_match_returns_empty(self):
        """T4: Non-conditional content yields no rules."""
        mem = MemoryEntry(
            id="mem-004",
            content="今天天气不错，适合散步",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 0

    def test_unless_rule(self):
        """T5: Extract 除非...否则... rule."""
        mem = MemoryEntry(
            id="mem-005",
            content="除非用户明确要求，否则不要提供医疗建议",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 1
        assert "用户明确要求" in rules[0].trigger
        assert "不要提供医疗建议" in rules[0].action

    def test_min_confidence_filter(self):
        """T6: Very short conditions filtered by min_confidence."""
        mem = MemoryEntry(
            id="mem-006",
            content="如果A就B",
            memory_type="episodic",
            branch_id="main",
        )
        rules = self.distiller.distill([mem])
        assert len(rules) == 0
