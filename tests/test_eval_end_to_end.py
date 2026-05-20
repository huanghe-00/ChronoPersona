"""End-to-end evaluation baseline tests."""

from typing import List

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from evaluation.baseline import VectorRAGBaseline
from evaluation.metrics import Metrics


class TestEvalEndToEnd:
    """Automated evaluation asserting Recall@K baseline for RAG retrieval."""

    def test_recall_at_k_meets_threshold(self) -> None:
        """T01: VectorRAGBaseline achieves Recall@K >= 0.6 on simple scenario."""
        baseline = VectorRAGBaseline()

        memories: List[MemoryEntry] = [
            MemoryEntry(id="m1", content="我喜欢吃川菜，特别是麻辣火锅"),
            MemoryEntry(id="m2", content="今天天气很好，适合去公园散步"),
            MemoryEntry(id="m3", content="昨晚失眠了，可能是因为工作压力大"),
        ]
        baseline.index(memories, branch_id="main")

        retrieved = baseline.retrieve("我喜欢辣的食物", branch_id="main", top_k=3)
        recall = Metrics.recall_at_k(retrieved, expected_ids=["m1"], k=3)

        assert recall >= 0.6, f"Recall@3 = {recall:.2f}, expected >= 0.6"

    def test_mrr_positive_when_relevant_exists(self) -> None:
        """T02: MRR is non-zero when relevant memory is retrievable."""
        baseline = VectorRAGBaseline()

        memories: List[MemoryEntry] = [
            MemoryEntry(id="m1", content="用户喜欢川菜"),
            MemoryEntry(id="m2", content="用户喜欢粤菜"),
        ]
        baseline.index(memories, branch_id="main")

        retrieved = baseline.retrieve("川菜", branch_id="main", top_k=2)
        mrr = Metrics.mrr(retrieved, expected_ids=["m1"])

        assert mrr > 0.0, f"MRR = {mrr:.2f}, expected > 0"

    def test_empty_expected_returns_zero(self) -> None:
        """T03: Metrics handle empty expected list gracefully."""
        baseline = VectorRAGBaseline()
        baseline.index([MemoryEntry(id="m1", content="test")], branch_id="main")

        retrieved = baseline.retrieve("test", branch_id="main", top_k=1)
        recall = Metrics.recall_at_k(retrieved, expected_ids=[], k=1)

        assert recall == 0.0
