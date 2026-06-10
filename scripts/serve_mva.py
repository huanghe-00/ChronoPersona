
#!/usr/bin/env python3
"""MVA WebSocket server for ChronoPersona.

Zero-dependency HTTP health check on port 8765.
WebSocket endpoint on ws://localhost:8765/ws.
"""

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import websockets

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default logging


def start_http_server(port: int = 8765):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"HTTP health check running on http://0.0.0.0:{port}/health")


async def websocket_handler(websocket, path):
    """Handle WebSocket connections."""
    # v1.1.0: API Key authentication skeleton (production baseline)
    api_key = os.environ.get("MVA_API_KEY")
    if api_key:
        auth_header = websocket.request_headers.get("Authorization", "")
        expected = f"Bearer {api_key}"
        if auth_header != expected:
            print(f"[Auth] Failed: expected {expected}, got {auth_header}")
            await websocket.close(1008, "Invalid API key")
            return

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
    start_http_server(port)
    start_server = websockets.serve(websocket_handler, "0.0.0.0", port)
    asyncio.get_event_loop().run_until_complete(start_server)
    print(f"WebSocket server running on ws://0.0.0.0:{port}/ws")
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
