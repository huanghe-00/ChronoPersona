"""A4-A5 adversarial evaluation tests."""

import pytest

from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder
from chronopersona.memory_system.l2_episodic.simple_store import SimpleEpisodicStore
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder


class TestA4SharedMain:
    """A4: Main branch shared facts retrieval."""

    def test_main_branch_recall_positive(self) -> None:
        """T01: Main branch facts are retrievable with positive recall."""
        scenario = ScenarioBuilder.build_a4_shared_main()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        for mem in scenario.memories:
            store.add(mem, branch_id=scenario.branch_id)

        ctx = store.retrieve("我叫什么名字", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        recall = Metrics.recall_at_k(retrieved_ids, scenario.expected_memory_ids[:1], k=5)
        assert recall > 0.0

    def test_main_branch_location_recall(self) -> None:
        """T02: Location fact is retrievable."""
        scenario = ScenarioBuilder.build_a4_shared_main()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        for mem in scenario.memories:
            store.add(mem, branch_id=scenario.branch_id)

        ctx = store.retrieve("我住在哪里", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        assert "a4-m2" in retrieved_ids


class TestA5MultiDeviceConflict:
    """A5: Multi-device conflict detection — both versions retained."""

    def test_conflict_both_versions_retrieved(self) -> None:
        """T01: Both conflicting preference versions are in top results."""
        scenario = ScenarioBuilder.build_a5_multi_device_conflict()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        for mem in scenario.memories:
            store.add(mem, branch_id=scenario.branch_id)

        ctx = store.retrieve("我喜欢什么菜系", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        assert "a5-m1" in retrieved_ids
        assert "a5-m2" in retrieved_ids

    def test_conflict_recall_at_k(self) -> None:
        """T02: Recall@5 covers both conflict versions."""
        scenario = ScenarioBuilder.build_a5_multi_device_conflict()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        for mem in scenario.memories:
            store.add(mem, branch_id=scenario.branch_id)

        ctx = store.retrieve("我喜欢什么菜系", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        recall = Metrics.recall_at_k(retrieved_ids, scenario.expected_memory_ids, k=5)
        assert recall > 0.0
