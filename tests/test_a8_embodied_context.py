"""A8: Embodied perception influences prompt content."""

import pytest

from chronopersona.agent_core.state_machine import StateMachineAgentCore
from chronopersona.contracts.schemas import EmbodiedState, RetrievedContext
from chronopersona.mocks.mock_memory_store import MockMemoryStore
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestA8EmbodiedContext:
    """A8: 2D environment state appears in LLM prompt."""

    def test_kitchen_fov_in_prompt(self) -> None:
        """T01: Kitchen objects appear in prompt."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        es = EmbodiedState(x=3.0, y=4.0, theta=0.0, fov_objects=["fridge", "stove"])
        prompt = core._build_prompt("我饿了", ctx, "main", embodied_state=es)
        assert "fridge" in prompt
        assert "stove" in prompt

    def test_living_room_fov_in_prompt(self) -> None:
        """T02: Living room objects appear in prompt."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        es = EmbodiedState(x=10.0, y=10.0, theta=1.57, fov_objects=["sofa", "tv"])
        prompt = core._build_prompt("我饿了", ctx, "main", embodied_state=es)
        assert "sofa" in prompt
        assert "tv" in prompt

    def test_no_embodied_state_omits_section(self) -> None:
        """T03: Missing embodied_state omits section from prompt."""
        core = StateMachineAgentCore(
            memory_store=MockMemoryStore(),
            model_router=MockModelRouter(),
        )
        ctx = RetrievedContext(episodic_memories=[], total_tokens=0)
        prompt = core._build_prompt("hi", ctx, "main")
        assert "[Embodied State]" not in prompt
