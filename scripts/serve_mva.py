"""MVA launch script: WebSocket gateway + MockAgentCore + GridWorldAdapter."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


def main() -> None:
    """Start MVA server with concrete GridWorldAdapter."""
    adapter = GridWorldAdapter(grid_width=20, grid_height=20, fov_range=5.0)
    adapter.add_object("agent-1", "sofa", x=2.0, y=3.0)
    adapter.add_object("agent-1", "table", x=3.0, y=2.0)

    core = StateMachineAgentCore(
        memory_store=MockMemoryStore(),
        model_router=MockModelRouter(),
    )
    gateway = WebSocketGateway(core, host="0.0.0.0", port=8765)

    print(f"MVA server starting on ws://{gateway._host}:{gateway._port}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
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
