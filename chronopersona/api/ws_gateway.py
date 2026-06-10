"""Minimal WebSocket gateway for real-time agent interaction (MVA).

W7+: Replaces stub with python-socketio or FastAPI WebSocket.
"""

from typing import Any, Dict

from loguru import logger

from chronopersona.contracts.interfaces import AbstractAgentCore


class WebSocketGateway:
    """MVA WebSocket gateway handling chat messages and embodied state."""

    def __init__(
        self,
        agent_core: AbstractAgentCore,
        host: str = "0.0.0.0",
        port: int = 8765,
    ) -> None:
        self._agent_core = agent_core
        self._host = host
        self._port = port
        self._clients: Dict[str, Any] = {}

    def register_client(self, client_id: str, socket: Any) -> None:
        """Register a connected client (MVA: no-op stub)."""
        self._clients[client_id] = socket
        logger.info("Client registered: {} (total: {})", client_id, len(self._clients))

    def unregister_client(self, client_id: str) -> None:
        """Remove a disconnected client."""
        self._clients.pop(client_id, None)
        logger.info("Client unregistered: {}", client_id)

    def handle_message(self, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous handler for incoming chat message.

        Args:
            client_id: Unique connection identifier.
            payload: Must contain 'message' and optional 'branch_id'.

        Returns:
            Response dict with reply_text, emotion_state, action_plan, branch_id.

        Raises:
            ValueError: If message is empty or branch_id is missing.
        """
        branch_id = payload.get("branch_id", "main")
        user_input = payload.get("message", "")
        if not user_input:
            raise ValueError("message must not be empty")
        if not branch_id:
            raise ValueError("branch_id must not be empty")

        # v1.1.0: Branch access audit hook (skeleton for RBAC)
        logger.info(
            "Access audit: client={} branch={} message_len={}",
            client_id,
            branch_id,
            len(user_input),
        )

        # v1.1.0: Inject embodied state if adapter is available
        embodied_state = None
        if hasattr(self._agent_core, "get_embodied_state"):
            try:
                embodied_state = self._agent_core.get_embodied_state()
            except Exception as e:
                logger.warning("Failed to get embodied state: {}", e)

        out = self._agent_core.run_turn(
            user_input,
            branch_id=branch_id,
            embodied_state=embodied_state,
        )
        return {
            "reply_text": out.reply_text,
            "emotion_state": {
                "current_state": out.emotion_state.current_state.value,
                "intensity": out.emotion_state.intensity,
            },
            "action_plan": {
                "action_token": out.action_plan.action_token if out.action_plan else None,
                "reasoning": out.action_plan.reasoning if out.action_plan else None,
            } if out.action_plan else None,
            "branch_id": branch_id,
        }

    def broadcast_state(self, state: Dict[str, Any]) -> int:
        """Broadcast embodied state to all connected clients.

        MVA: Synchronous broadcast for simple servers.
        Returns:
            Number of clients broadcasted to.
        """
        import json

        sent = 0
        for client_id, socket in list(self._clients.items()):
            try:
                if hasattr(socket, "send"):
                    socket.send(json.dumps({"event": "embodied.state", "data": state}))
                    sent += 1
            except Exception as e:
                logger.warning("Failed to broadcast to {}: {}", client_id, e)
                self.unregister_client(client_id)
        logger.info("Broadcast embodied state to {}/{} clients", sent, len(self._clients))
        return len(self._clients)

    async def broadcast_state_async(self, state: Dict[str, Any]) -> int:
        """Async broadcast for asyncio-based servers."""
        import json

        sent = 0
        for client_id, socket in list(self._clients.items()):
            try:
                await socket.send(json.dumps({"event": "embodied.state", "data": state}))
                sent += 1
            except Exception as e:
                logger.warning("Failed to broadcast to {}: {}", client_id, e)
                self.unregister_client(client_id)
        return sent
