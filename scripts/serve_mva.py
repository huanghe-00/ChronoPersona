
#!/usr/bin/env python3
"""MVA WebSocket server for ChronoPersona.

WebSocket endpoint on ws://localhost:8765/ws
HTTP health check on http://localhost:8765/health
"""

import asyncio
import functools
import json
import os

import websockets
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


async def process_request(path, request_headers):
    """Handle HTTP health check before WebSocket upgrade."""
    if path == "/health":
        return (200, [("Content-type", "application/json")], b'{"status":"ok"}')
    return None


async def websocket_handler(websocket, path, gateway, adapter):
    """Handle WebSocket connections with shared state."""
    # v1.1.0: API Key authentication skeleton (production baseline)
    api_key = os.environ.get("MVA_API_KEY")
    if api_key:
        auth_header = websocket.request_headers.get("Authorization", "")
        expected = f"Bearer {api_key}"
        if auth_header != expected:
            print(f"[Auth] Failed: expected {expected}, got {auth_header}")
            await websocket.close(1008, "Invalid API key")
            return

    client_id = str(id(websocket))
    gateway.register_client(client_id, websocket)

    print(f"Client connected: {client_id}")
    try:
        async for message in websocket:
            payload = json.loads(message)
            response = gateway.handle_message(client_id, payload)
            await websocket.send(json.dumps({"event": "chat.reply", "data": response}))

            # Push real embodied state from adapter
            embodied = adapter.get_perception("default")
            state = {
                "x": embodied.x,
                "y": embodied.y,
                "theta": embodied.theta,
                "fov_objects": embodied.fov_objects,
                "action_token": (
                    response.get("action_plan", {}).get("action_token")
                    if response.get("action_plan")
                    else None
                ),
            }
            await gateway.broadcast_state_async(state)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        gateway.unregister_client(client_id)
        print(f"Client disconnected: {client_id}")


def main():
    port = int(os.environ.get("PORT", "8765"))
    static_port = int(os.environ.get("STATIC_PORT", "8080"))

    # MVA: single-threaded HTTP is sufficient for frontend static files
    frontend_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "frontend"
    )

    class FrontendHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

    def start_static_server() -> None:
        server = HTTPServer(("0.0.0.0", static_port), FrontendHandler)
        print(f"Frontend static server running on http://0.0.0.0:{static_port}")
        server.serve_forever()

    static_thread = threading.Thread(target=start_static_server, daemon=True)
    static_thread.start()

    from chronopersona.embodied.grid_world_adapter import GridWorldAdapter

    adapter = GridWorldAdapter()
    # Align initial pose with frontend hard-coded initial state
    adapter._agents["default"] = (3.0, 4.0, 0.0)

    agent_core = StateMachineAgentCore(
        memory_store=MockMemoryStore(),
        model_router=MockModelRouter(),
        embodied_adapter=adapter,
    )
    gateway = WebSocketGateway(agent_core=agent_core)

    handler = functools.partial(websocket_handler, gateway=gateway, adapter=adapter)
    start_server = websockets.serve(
        handler, "0.0.0.0", port, process_request=process_request
    )
    asyncio.get_event_loop().run_until_complete(start_server)
    print(f"Server running on ws://0.0.0.0:{port}/ws (health: http://0.0.0.0:{port}/health)")
    print(f"Frontend: http://0.0.0.0:{static_port}")
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
