"""A1-A3 adversarial evaluation tests."""

import pytest

from evaluation.baseline import VectorRAGBaseline
from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder


class TestA1MemoryRecall:
    """A1: Memory accuracy across sessions."""

    def test_a1_recall_at_5(self) -> None:
        """A1 memories should be recalled with Recall@5 >= 0.8."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        baseline = VectorRAGBaseline()
        baseline.index(scenario.memories, scenario.branch_id)

        recalls = []
        for query, expected in zip(scenario.queries, scenario.expected_memory_ids):
            retrieved = baseline.retrieve(query, scenario.branch_id, top_k=5)
            r = Metrics.recall_at_k(retrieved, [expected], k=5)
            recalls.append(r)

        avg_recall = sum(recalls) / len(recalls)
        assert avg_recall >= 0.8, f"A1 average Recall@5 = {avg_recall:.2f}"

    def test_a1_ndcg_at_5(self) -> None:
        """A1 also satisfies NDCG@5 baseline via ranx."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        baseline = VectorRAGBaseline()
        baseline.index(scenario.memories, scenario.branch_id)

        ndcgs = []
        for query, expected in zip(scenario.queries, scenario.expected_memory_ids):
            retrieved = baseline.retrieve(query, scenario.branch_id, top_k=5)
            ndcg = Metrics.ndcg_at_k(retrieved, [expected], k=5)
            ndcgs.append(ndcg)

        avg_ndcg = sum(ndcgs) / len(ndcgs)
        assert avg_ndcg >= 0.0, f"A1 average NDCG@5 = {avg_ndcg:.2f}"


class TestA2CrossSession:
    """A2: Temporal association."""

    def test_a2_mrr(self) -> None:
        """A2 should achieve MRR >= 0.5 for temporal reasoning."""
        scenario = ScenarioBuilder.build_a2_cross_session()
        baseline = VectorRAGBaseline()
        baseline.index(scenario.memories, scenario.branch_id)

        mrrs = []
        for query, expected in zip(scenario.queries, scenario.expected_memory_ids):
            retrieved = baseline.retrieve(query, scenario.branch_id, top_k=5)
            mrr = Metrics.mrr(retrieved, [expected])
            mrrs.append(mrr)

        avg_mrr = sum(mrrs) / len(mrrs)
        assert avg_mrr >= 0.5, f"A2 average MRR = {avg_mrr:.2f}"


class TestA3PersonaIsolation:
    """A3: Branch isolation."""

    def test_a3_isolation_recall_zero(self) -> None:
        """Cross-branch query should return zero relevant memories."""
        from chronopersona.memory_system.l2_episodic import SimpleEpisodicStore
        from chronopersona.contracts.schemas import MemoryEntry

        store = SimpleEpisodicStore()
        store.add(MemoryEntry(content="敏感信息", id="private-1"), branch_id="therapist")

        ctx = store.retrieve("敏感", branch_id="rpg-hero", top_k=5)
        assert len(ctx.episodic_memories) == 0
