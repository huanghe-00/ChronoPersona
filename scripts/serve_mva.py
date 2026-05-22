"""MVA launch script: WebSocket gateway + MockAgentCore + GridWorldAdapter."""

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
