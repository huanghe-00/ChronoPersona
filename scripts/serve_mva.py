
#!/usr/bin/env python3
"""MVA WebSocket server for ChronoPersona.

WebSocket endpoint on ws://localhost:8765/ws
HTTP health check on http://localhost:8765/health
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for absolute imports like
# `from chronopersona.agent_core...` to work regardless of
# invocation directory or PYTHONPATH configuration.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import asyncio
import functools
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import websockets
from loguru import logger

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.api.ws_gateway import WebSocketGateway
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.agent_core.action_planner import ActionPlanner
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
            logger.warning("[Auth] Failed: expected {}, got {}", expected, auth_header)
            await websocket.close(1008, "Invalid API key")
            return

    client_id = str(id(websocket))
    gateway.register_client(client_id, websocket)

    logger.info("Client connected: {}", client_id)
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
        logger.info("Client disconnected: {}", client_id)


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
        logger.info("Frontend static server running on http://0.0.0.0:{}", static_port)
        server.serve_forever()

    static_thread = threading.Thread(target=start_static_server, daemon=True)
    static_thread.start()

    habitat_scene = os.environ.get("HABITAT_SCENE")
    if habitat_scene:
        from chronopersona.embodied.habitat_adapter import HabitatAdapter
        adapter = HabitatAdapter(scene_path=habitat_scene, agent_id="default")
        logger.info("Using HabitatAdapter (3D) with scene: {}", habitat_scene)
    else:
        from chronopersona.embodied.grid_world_adapter import GridWorldAdapter
        adapter = GridWorldAdapter()
        # Align initial pose with frontend hard-coded initial state
        adapter._agents["default"] = (3.0, 4.0, 0.0)
        adapter.add_object("default", "沙发", 2.0, 3.0)
        adapter.add_object("default", "床", 8.0, 12.0)
        adapter.add_object("default", "桌子", 3.0, 2.0)
        adapter.add_object("default", "厨房", 15.0, 5.0)
        adapter.add_object("default", "椅子", 5.0, 5.0)
        adapter.add_object("default", "冰箱", 10.0, 5.0)
        adapter.add_object("default", "茶几", 4.0, 3.0)
        logger.info("Using GridWorldAdapter (2D)")

    agent_core = StateMachineAgentCore(
        memory_store=MockMemoryStore(),
        model_router=MockModelRouter(),
        embodied_adapter=adapter,
        action_planner=ActionPlanner(),
    )

    # v1.1.0: 正式化位置感知演示逻辑（已脱离 monkey-patch）
    # 位置感知回复在 _build_prompt 的 [Embodied State] 注入后，由 LLMNode 自然生成
    # 保留此注释以标记 MVA 演示能力已完成

    gateway = WebSocketGateway(
        agent_core=agent_core,
        speech_recognizer=None,  # MVA: ASR placeholder; future: Whisper.cpp
    )

    async def start_ws_server():
        return await websockets.serve(
            handler, "0.0.0.0", port, process_request=process_request,
            ping_interval=30, ping_timeout=60,
        )

    handler = functools.partial(websocket_handler, gateway=gateway, adapter=adapter)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = loop.run_until_complete(start_ws_server())
    logger.info("Server running on ws://0.0.0.0:{}/ws (health: http://0.0.0.0:{}/health)", port, port)
    logger.info("Frontend: http://0.0.0.0:{}", static_port)
    loop.run_forever()


if __name__ == "__main__":
    main()
