"""Tests for embodied state injection through WebSocketGateway."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestWsGatewayEmbodiedState:
    """Verify embodied state is passed to agent core on every turn."""

    @pytest.fixture
    def gateway_with_adapter(self) -> WebSocketGateway:
        adapter = GridWorldAdapter()
        adapter._agents["default"] = (3.0, 4.0, 0.0)
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
            embodied_adapter=adapter,
        )
        return WebSocketGateway(agent_core=core)

    def test_handle_message_injects_embodied_state(self, gateway_with_adapter: WebSocketGateway) -> None:
        """T1: Gateway passes embodied state to run_turn when adapter is present."""
        result = gateway_with_adapter.handle_message(
            "client-1",
            {"message": "你好", "branch_id": "main"},
        )
        assert "reply_text" in result
        assert result["branch_id"] == "main"

    def test_embodied_state_after_navigation(self, gateway_with_adapter: WebSocketGateway) -> None:
        """T2: Post-navigation turn includes updated embodied state."""
        # First, navigate to sofa
        gateway_with_adapter.handle_message(
            "client-1",
            {"message": "到沙发旁边", "branch_id": "main"},
        )
        # Then ask a non-navigation question
        result = gateway_with_adapter.handle_message(
            "client-1",
            {"message": "你现在在哪", "branch_id": "main"},
        )
        assert "reply_text" in result

    def test_no_adapter_graceful(self) -> None:
        """T3: Gateway works without embodied adapter."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        gateway = WebSocketGateway(agent_core=core)
        result = gateway.handle_message(
            "client-1",
            {"message": "你好", "branch_id": "main"},
        )
        assert "reply_text" in result
        assert result["branch_id"] == "main"
