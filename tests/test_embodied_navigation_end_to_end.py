"""End-to-end tests for embodied semantic navigation bypass."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestEmbodiedNavigationEndToEnd:
    """Verify navigation bypass pipeline: input → parse → move → reply → memory."""

    @pytest.fixture
    def core(self) -> StateMachineAgentCore:
        adapter = GridWorldAdapter()
        adapter._agents["default"] = (3.0, 4.0, 0.0)
        return StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )

    def test_navigate_to_known_target_success(self, core: StateMachineAgentCore) -> None:
        """T1: Known target teleports and returns inquiry reply."""
        out = core.run_turn("到沙发旁边", branch_id="main")
        assert "已到达" in out.reply_text
        assert "沙发" in out.reply_text
        assert "还需要什么" in out.reply_text

    def test_navigate_to_unknown_target_failure(self, core: StateMachineAgentCore) -> None:
        """T2: Unknown target returns graceful failure."""
        out = core.run_turn("去火星", branch_id="main")
        assert "无法找到" in out.reply_text
        assert "火星" in out.reply_text

    def test_navigation_memory_persisted_to_l2(self, core: StateMachineAgentCore) -> None:
        """T3: Navigation event is written to L2 episodic memory."""
        core.run_turn("去厨房", branch_id="main")

        store = core._memory_store
        nav_memories = [
            m for m in store._memories.get("main", [])
            if getattr(m, "memory_type", None) == "episodic" and "[导航]" in m.content
        ]
        assert len(nav_memories) == 1
        assert "厨房" in nav_memories[0].content
        assert nav_memories[0].branch_id == "main"

        # v1.1.0: Provenance chain verification via metadata
        assert nav_memories[0].metadata.get("source") == "embodied_navigation_bypass"
        assert nav_memories[0].metadata.get("nav_target") == "厨房"
        assert nav_memories[0].metadata.get("extraction_model") == "heuristic_rule"
        assert nav_memories[0].metadata.get("extraction_confidence") == 1.0

    def test_consecutive_navigation_stateful(self, core: StateMachineAgentCore) -> None:
        """T4: Consecutive navigation respects current position (no reset)."""
        core.run_turn("到沙发旁边", branch_id="main")
        adapter = core._embodied_adapter
        assert adapter is not None
        state = adapter.get_perception("default")
        assert state.x == 2.0
        assert state.y == 3.0

        core.run_turn("去床那里", branch_id="main")
        state = adapter.get_perception("default")
        assert state.x == 8.0
        assert state.y == 12.0
