"""Tests for correlation miner implementations."""

from typing import List

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.memory_system.l3_semantic.correlation_miner import (
    SimpleCorrelationMiner,
)
from chronopersona.mocks.mock_correlation_miner import MockCorrelationMiner


class TestSimpleCorrelationMiner:
    """Unit tests for SimpleCorrelationMiner."""

    def test_mine_correlations_returns_correlated_ids(self) -> None:
        """T01: Correlated memories are returned."""
        miner = SimpleCorrelationMiner()
        memories = [
            MemoryEntry(id="m1", content="失眠 压力 工作"),
            MemoryEntry(id="m2", content="压力 工作 加班"),
            MemoryEntry(id="m3", content="火锅 美食 开心"),
        ]
        correlated = miner.mine_correlations(
            memories, branch_id="main", min_confidence=0.4
        )
        assert "m1" in correlated
        assert "m2" in correlated
        assert "m3" not in correlated

    def test_mine_correlations_respects_min_confidence(self) -> None:
        """T02: min_confidence filters out weak correlations."""
        miner = SimpleCorrelationMiner()
        memories = [
            MemoryEntry(id="m1", content="a b c"),
            MemoryEntry(id="m2", content="a b d"),
        ]
        # Jaccard = 2/4 = 0.5
        correlated = miner.mine_correlations(
            memories, branch_id="main", min_confidence=0.6
        )
        assert correlated == []

    def test_get_correlation_score_identical(self) -> None:
        """T03: Identical content yields score 1.0."""
        miner = SimpleCorrelationMiner()
        mem = MemoryEntry(id="m1", content="a b c")
        score = miner.get_correlation_score(mem, mem, branch_id="main")
        assert score == 1.0

    def test_get_correlation_score_no_overlap(self) -> None:
        """T04: No overlap yields score 0.0."""
        miner = SimpleCorrelationMiner()
        mem_a = MemoryEntry(id="m1", content="a b")
        mem_b = MemoryEntry(id="m2", content="c d")
        score = miner.get_correlation_score(mem_a, mem_b, branch_id="main")
        assert score == 0.0


class TestMockCorrelationMiner:
    """Unit tests for MockCorrelationMiner."""

    def test_mock_returns_predefined_ids(self) -> None:
        """T05: Mock returns predefined correlated IDs."""
        mock = MockCorrelationMiner()
        mock.set_correlated_ids(["m1", "m3"])
        memories: List[MemoryEntry] = []
        correlated = mock.mine_correlations(memories, branch_id="main")
        assert correlated == ["m1", "m3"]

    def test_mock_returns_predefined_score(self) -> None:
        """T06: Mock returns predefined correlation score."""
        mock = MockCorrelationMiner()
        mock.set_score("m1", "m2", 0.85)
        mem_a = MemoryEntry(id="m1", content="")
        mem_b = MemoryEntry(id="m2", content="")
        score = mock.get_correlation_score(mem_a, mem_b, branch_id="main")
        assert score == 0.85

    def test_mock_default_score_zero(self) -> None:
        """T07: Mock returns 0.0 for unknown pair."""
        mock = MockCorrelationMiner()
        mem_a = MemoryEntry(id="m1", content="")
        mem_b = MemoryEntry(id="m2", content="")
        score = mock.get_correlation_score(mem_a, mem_b, branch_id="main")
        assert score == 0.0
