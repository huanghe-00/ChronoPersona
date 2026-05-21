"""Regression tests for evaluation baselines.

Guards against A1/A2 metric degradation on code changes.
"""

import pytest

from chronopersona.contracts.schemas import MemoryEntry
from evaluation.baseline import VectorRAGBaseline
from evaluation.metrics import Metrics


class TestEvalRegression:
    """Regression guard for A1/A2 evaluation metrics."""

    def test_a1_recall_at_k_stable(self) -> None:
        """T01: A1 Recall@K must not drop below 0.6."""
        baseline = VectorRAGBaseline()
        baseline.index(
            [
                MemoryEntry(id="m1", content="我喜欢吃川菜"),
                MemoryEntry(id="m2", content="今天天气很好"),
            ],
            branch_id="main",
        )
        retrieved = baseline.retrieve("我喜欢辣的食物", branch_id="main", top_k=2)
        recall = Metrics.recall_at_k(retrieved, expected_ids=["m1"], k=2)
        assert recall >= 0.6, f"A1 Recall@2 degraded to {recall:.2f}"

    def test_a2_mrr_stable(self) -> None:
        """T02: A2 MRR must remain positive for temporal queries."""
        baseline = VectorRAGBaseline()
        baseline.index(
            [
                MemoryEntry(id="m1", content="我遇到了一个bug"),
                MemoryEntry(id="m2", content="后来修好了"),
            ],
            branch_id="main",
        )
        retrieved = baseline.retrieve("bug 后来怎样了", branch_id="main", top_k=2)
        mrr = Metrics.mrr(retrieved, expected_ids=["m1", "m2"])
        assert mrr > 0.0, f"A2 MRR degraded to {mrr:.2f}"

    def test_metrics_handle_empty_gracefully(self) -> None:
        """T03: Metrics return 0.0 for empty inputs, not crash."""
        recall = Metrics.recall_at_k([], expected_ids=["m1"], k=1)
        assert recall == 0.0
        mrr = Metrics.mrr([], expected_ids=["m1"])
        assert mrr == 0.0
