#!/usr/bin/env python3
"""MVA HTTP API server: zero-dependency, standard library only."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class _SilentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class ChatHandler(_SilentHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        if self.path != "/chat":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)
            response = self.server.gateway.handle_message(
                payload.get("client_id", "anonymous"),
                payload,
            )
            self._send_json(200, response)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            self._send_json(400, {"error": f"Bad request: {e}"})

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "version": "1.0-mva"})
        else:
            self._send_json(404, {"error": "Not found"})


def main():
    core = StateMachineAgentCore(
        memory_store=MockMemoryStore(),
        model_router=MockModelRouter(),
    )
    gateway = WebSocketGateway(core)

    server = HTTPServer(("0.0.0.0", 8765), ChatHandler)
    server.gateway = gateway  # type: ignore[attr-defined]

    print("=" * 50)
    print("ChronoPersona MVA HTTP Server")
    print("=" * 50)
    print("Endpoints:")
    print("  POST http://0.0.0.0:8765/chat")
    print("    Body: {\"message\": \"...\", \"branch_id\": \"...\"}")
    print("    Returns: {\"reply_text\", \"emotion_state\", \"action_plan\", ...}")
    print("  GET  http://0.0.0.0:8765/health")
    print("=" * 50)
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
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

    agent_core = StateMachineAgentCore(
        memory_store=MockMemoryStore(),
        model_router=MockModelRouter(),
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

            # Push embodied state stub (v0.7.0: static demo state)
            state = {
                "x": 3,
                "y": 4,
                "theta": 0.0,
                "fov_objects": ["sofa", "table"],
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
