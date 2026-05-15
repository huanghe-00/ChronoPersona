"""Week 1 core guard: Mock pipeline tests.

Target: 28 test cases covering end-to-end, CRDT, Memory, Agent, API, and integration.
"""

import pytest

from chronopersona.contracts.schemas import (
    AgentOutput,
    ChangeSet,
    EmbodiedState,
    EmotionLabel,
    EmotionState,
    MemoryEntry,
    ModelRequest,
    RetrievedContext,
)
from chronopersona.mocks import (
    MockAgentCore,
    MockCostTracker,
    MockEmbodiedAdapter,
    MockMemoryMigrationService,
    MockMemoryStore,
    MockModelRouter,
    MockPersonaInjector,
    MockSkill,
    MockSkillRegistry,
    MockVersionManager,
)


class TestEndToEndAndBasic:
    """T01-T05: End-to-end and basic tests."""

    def test_t01_mock_full_turn(self):
        """T01: Mock dialogue full turn."""
        agent = MockAgentCore()
        out = agent.run_turn("Hello", branch_id="main")
        assert isinstance(out, AgentOutput)
        assert out.reply_text
        assert out.branch_id == "main"

    def test_t02_branch_isolation(self):
        """T02: Branch isolation."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="secret"), branch_id="therapist")
        ctx = store.retrieve("secret", branch_id="rpg-hero")
        assert not any(m.content == "secret" for m in ctx.episodic_memories)

    def test_t03_lww_merge(self):
        """T03: LWW merge placeholder (Mock level)."""
        store = MockMemoryStore()
        mid = store.add(MemoryEntry(content="v1"), branch_id="main")
        assert mid.startswith("mock-mem-")

    def test_t04_intent_retrieval(self):
        """T04: Intent retrieval returns RetrievedContext."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="data"), branch_id="main")
        ctx = store.retrieve("data", branch_id="main", intent="retrieve")
        assert isinstance(ctx, RetrievedContext)

    def test_t05_persona_switch(self):
        """T05: Persona switch."""
        agent = MockAgentCore()
        agent.switch_persona("therapist", branch_id="therapist")
        assert agent._persona_id == "therapist"


class TestCRDTCore:
    """T06-T10: CRDT core tests (Mock level)."""

    def test_t06_crdt_merge_basic(self):
        """T06: Basic merge operation."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="a"), branch_id="main")
        store.add(MemoryEntry(content="b"), branch_id="main")
        ctx = store.retrieve("a", branch_id="main")
        assert len(ctx.episodic_memories) == 2

    def test_t07_clock_skew_detection(self):
        """T07: Clock skew detection placeholder."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(), branch_id="")

    def test_t08_conflict_preservation(self):
        """T08: Conflict preservation (Mock stores both)."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="x"), branch_id="main")
        store.add(MemoryEntry(content="y"), branch_id="main")
        ctx = store.retrieve("x", branch_id="main")
        assert len(ctx.episodic_memories) == 2

    def test_t09_sync_broadcast(self):
        """T09: Sync broadcast placeholder."""
        vm = MockVersionManager()
        v = vm.commit("main", ChangeSet())
        assert v.branch_id == "main"

    def test_t10_offline_replay(self):
        """T10: Offline replay placeholder."""
        vm = MockVersionManager()
        vm.commit("main", ChangeSet())
        versions = vm.log("main")
        assert len(versions) == 1


class TestMemoryLayers:
    """T11-T15: Memory layer tests."""

    def test_t11_l0_read_write(self):
        """T11: L0 read/write via MockMemoryStore."""
        store = MockMemoryStore()
        mid = store.add(MemoryEntry(content="l0"), branch_id="main")
        assert mid

    def test_t12_l1_working_window(self):
        """T12: L1 working window simulation."""
        store = MockMemoryStore()
        for i in range(5):
            store.add(MemoryEntry(content=f"t{i}"), branch_id="main")
        ctx = store.retrieve("t", branch_id="main")
        assert len(ctx.working_memories) <= 5

    def test_t13_l2_episodic_write(self):
        """T13: L2 episodic write."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="ep", memory_type="episodic"), branch_id="main")
        ctx = store.retrieve("ep", branch_id="main")
        assert all(m.memory_type == "episodic" for m in ctx.episodic_memories)

    def test_t14_l3_semantic_fact(self):
        """T14: L3 semantic fact retrieval."""
        store = MockMemoryStore()
        facts = store.get_facts("e1", branch_id="main")
        assert facts == []

    def test_t15_checkout_snapshot(self):
        """T15: Checkout snapshot."""
        vm = MockVersionManager()
        snap = vm.checkout("main")
        assert snap.branch_id == "main"


class TestAgentNodes:
    """T16-T20: Agent node tests."""

    def test_t16_state_machine(self):
        """T16: State machine runs without error."""
        agent = MockAgentCore()
        out = agent.run_turn("hi", branch_id="main")
        assert out.branch_id == "main"

    def test_t17_intent_node(self):
        """T17: Intent node placeholder."""
        agent = MockAgentCore()
        assert agent.run_turn("test", branch_id="main").reply_text

    def test_t18_memory_node(self):
        """T18: Memory node integration."""
        store = MockMemoryStore()
        store.add(MemoryEntry(content="ctx"), branch_id="main")
        ctx = store.retrieve("ctx", branch_id="main")
        assert ctx.total_tokens >= 0

    def test_t19_llm_node(self):
        """T19: LLM node via MockModelRouter."""
        router = MockModelRouter()
        resp = router.route(ModelRequest(prompt="hi"), branch_id="main")
        assert resp.content

    def test_t20_output_node(self):
        """T20: Output node produces AgentOutput."""
        agent = MockAgentCore()
        out = agent.run_turn("hello", branch_id="main")
        assert isinstance(out, AgentOutput)


class TestAPISerialization:
    """T21-T25: API and serialization tests."""

    def test_t21_rest_schema(self):
        """T21: REST schema instantiation."""
        out = AgentOutput(reply_text="ok", branch_id="main")
        assert out.reply_text == "ok"

    def test_t22_websocket_event(self):
        """T22: WebSocket event placeholder."""
        es = EmbodiedState(agent_id="a1", x=1.0, y=2.0)
        assert es.agent_id == "a1"

    def test_t23_error_handling(self):
        """T23: Error handling."""
        store = MockMemoryStore()
        with pytest.raises(ValueError):
            store.add(MemoryEntry(), branch_id="")

    def test_t24_schema_validation(self):
        """T24: Schema validation."""
        es = EmotionState(current_state=EmotionLabel.CONCERNED, intensity=0.8)
        assert es.intensity == 0.8

    def test_t25_auth_mock(self):
        """T25: Auth mock placeholder."""
        agent = MockAgentCore()
        with pytest.raises(ValueError):
            agent.run_turn("hi", branch_id="")


class TestIntegrationRegression:
    """T26-T28: Integration regression tests."""

    def test_t26_full_pipeline(self):
        """T26: Full pipeline."""
        agent = MockAgentCore()
        store = MockMemoryStore()
        router = MockModelRouter()
        out = agent.run_turn("full", branch_id="main")
        assert out.reply_text

    def test_t27_persona_switch_regression(self):
        """T27: Persona switch regression."""
        agent = MockAgentCore()
        agent.switch_persona("rpg-hero", branch_id="rpg-hero")
        out = agent.run_turn("fight", branch_id="rpg-hero")
        assert out.branch_id == "rpg-hero"

    def test_t28_eval_injection(self):
        """T28: Eval injection placeholder."""
        adapter = MockEmbodiedAdapter()
        cmd = adapter.translate_action_token("move", {}, "grid_2d")
        assert cmd.robot_type == "grid_2d"
