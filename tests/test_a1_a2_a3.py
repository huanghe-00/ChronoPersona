"""A1-A3 adversarial evaluation tests."""

import pytest

from evaluation.metrics import Metrics
from evaluation.scenarios import ScenarioBuilder
from chronopersona.memory_system.l2_episodic.simple_store import SimpleEpisodicStore
from chronopersona.memory_system.l2_episodic.embedder import MockBGEEmbedder
from chronopersona.contracts.schemas import RetrievedContext


class TestA1MemoryRecall:
    """A1: Cross-session factual retrieval."""

    def test_phone_number_recall(self) -> None:
        """T01: Phone number fact retrievable."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]

        ctx = store.retrieve("我的手机号", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        recall = Metrics.recall_at_k(retrieved_ids, [actual_ids[0]], k=5)
        assert recall > 0.0

    def test_pet_name_recall(self) -> None:
        """T02: Pet name fact retrievable."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]

        ctx = store.retrieve("我的狗", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        assert actual_ids[2] in retrieved_ids

    def test_workplace_recall(self) -> None:
        """T03: Workplace fact retrievable."""
        scenario = ScenarioBuilder.build_a1_memory_recall()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]

        ctx = store.retrieve("我在哪里工作", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        assert actual_ids[3] in retrieved_ids


class TestA2CrossSession:
    """A2: Temporal reasoning across sessions."""

    def test_scheme_final_status(self) -> None:
        """T04: Final scheme status (approved) retrievable."""
        scenario = ScenarioBuilder.build_a2_cross_session()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]

        ctx = store.retrieve("方案后来怎么样", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        assert actual_ids[-1] in retrieved_ids

    def test_scheme_approved_recall(self) -> None:
        """T05: Query 'approved' recalls final memory."""
        scenario = ScenarioBuilder.build_a2_cross_session()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        actual_ids = [store.add(mem, branch_id=scenario.branch_id) for mem in scenario.memories]

        ctx = store.retrieve("方案通过了吗", branch_id=scenario.branch_id, top_k=5)
        retrieved_ids = [m.id for m in ctx.episodic_memories]
        recall = Metrics.recall_at_k(retrieved_ids, [actual_ids[-1]], k=5)
        assert recall > 0.0


class TestA3PersonaIsolation:
    """A3: Branch isolation effectiveness."""

    def test_therapist_branch_no_main_leak(self) -> None:
        """T06: Main branch facts not visible in therapist branch."""
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())
        main_scenario = ScenarioBuilder.build_a4_shared_main()
        for mem in main_scenario.memories:
            store.add(mem, branch_id="main")

        ctx = store.retrieve("我叫什么名字", branch_id="therapist", top_k=5)
        assert len(ctx.episodic_memories) == 0

    def test_therapist_branch_empty_retrieval(self) -> None:
        """T07: Empty therapist branch returns empty context."""
        scenario = ScenarioBuilder.build_a3_persona_isolation()
        store = SimpleEpisodicStore(embedder=MockBGEEmbedder())

        ctx = store.retrieve("任何内容", branch_id=scenario.branch_id, top_k=5)
        assert isinstance(ctx, RetrievedContext)
        assert len(ctx.episodic_memories) == 0
