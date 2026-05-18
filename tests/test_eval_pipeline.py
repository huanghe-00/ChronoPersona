"""End-to-end evaluation pipeline tests."""

from evaluation.baseline import VectorRAGBaseline
from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder


class TestEvalPipeline:
    """Tests for evaluation framework integrity."""

    def test_pipeline_runs_without_error(self) -> None:
        """Full pipeline should execute and produce metrics."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        baseline = VectorRAGBaseline()
        baseline.index(scenario.memories, scenario.branch_id)

        results = []
        for query, expected in zip(scenario.queries, scenario.expected_memory_ids):
            retrieved = baseline.retrieve(query, scenario.branch_id, top_k=5)
            recall = Metrics.recall_at_k(retrieved, [expected], k=5)
            results.append({"query": query, "recall@5": recall})

        assert len(results) == len(scenario.queries)
        assert all(r["recall@5"] >= 0.0 for r in results)

    def test_metrics_edge_cases(self) -> None:
        """Metrics handle empty inputs and ranx-backed metrics work."""
        assert Metrics.recall_at_k([], ["a"], k=5) == 0.0
        assert Metrics.mrr([], ["a"]) == 0.0
        assert Metrics.ndcg_at_k([], ["a"], k=5) == 0.0
        assert Metrics.map([], ["a"]) == 0.0
        assert Metrics.answer_f1("", "test") == 0.0
        assert Metrics.answer_f1("test", "test") > 0.0

    def test_ranx_ndcg_and_map_positive(self) -> None:
        """ranx-backed NDCG and MAP return positive values for valid inputs."""
        retrieved = ["d1", "d2", "d3"]
        expected = ["d1"]
        assert Metrics.ndcg_at_k(retrieved, expected, k=5) > 0.0
        assert Metrics.map(retrieved, expected) > 0.0
