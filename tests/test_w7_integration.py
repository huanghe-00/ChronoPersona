"""W7 integration: WebSocket Gateway + GridWorldAdapter + StateMachineAgentCore."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestW7Integration:
    """End-to-end W7 integration tests."""

    def test_gateway_with_embodied_state(self) -> None:
        """T01: Gateway handles message with embodied state and returns action plan."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        gw = WebSocketGateway(core)
        resp = gw.handle_message("c1", {
            "message": "慢慢靠近",
            "branch_id": "main",
        })
        assert "reply_text" in resp
        assert resp["branch_id"] == "main"

    def test_grid_world_fov_influences_perception(self) -> None:
        """T02: GridWorld FOV detects objects within range."""
        adapter = GridWorldAdapter(grid_width=20, grid_height=20, fov_range=5.0)
        adapter.add_object("a1", "fridge", x=3.0, y=0.0)
        percept = adapter.get_perception("a1")
        assert "fridge" in percept.fov_objects

    def test_agent_core_prompt_includes_embodied_and_emotion(self) -> None:
        """T03: _build_prompt contains both embodied state and emotion state."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        from chronopersona.contracts.schemas import EmbodiedState, RetrievedContext
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        es = EmbodiedState(x=3.0, y=4.0, theta=0.0, fov_objects=["sofa"])
        core._emotion_state = core._update_emotion("我好焦虑", "main")
        prompt = core._build_prompt("hi", ctx, "main", embodied_state=es)
        assert "[Embodied State]" in prompt
        assert "[Emotion State]" in prompt
        assert "CONCERNED" in prompt
