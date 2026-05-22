"""Unit tests for WebSocketGateway."""

import pytest

from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.mocks.mock_agent_core import MockAgentCore


class TestWebSocketGateway:
    """Tests for MVA WebSocket gateway."""

    def test_handle_message_returns_reply(self) -> None:
        """T01: Gateway processes message and returns structured reply."""
        core = MockAgentCore()
        gw = WebSocketGateway(core)
        resp = gw.handle_message("c1", {"message": "hello", "branch_id": "main"})
        assert "reply_text" in resp
        assert resp["branch_id"] == "main"
        assert "emotion_state" in resp

    def test_handle_message_empty_raises_valueerror(self) -> None:
        """T02: Empty message raises ValueError."""
        core = MockAgentCore()
        gw = WebSocketGateway(core)
        with pytest.raises(ValueError):
            gw.handle_message("c1", {"message": "", "branch_id": "main"})

    def test_handle_message_missing_branch_defaults_to_main(self) -> None:
        """T03: Missing branch_id defaults to 'main'."""
        core = MockAgentCore()
        gw = WebSocketGateway(core)
        resp = gw.handle_message("c1", {"message": "hi"})
        assert resp["branch_id"] == "main"

    def test_broadcast_state_returns_client_count(self) -> None:
        """T04: Broadcast returns number of tracked clients."""
        core = MockAgentCore()
        gw = WebSocketGateway(core)
        gw.register_client("c1", None)
        gw.register_client("c2", None)
        count = gw.broadcast_state({"x": 0, "y": 0})
        assert count == 2
