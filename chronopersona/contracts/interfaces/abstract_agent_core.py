"""
Abstract interface for the Agent Core layer.

Defines the contract that any agent core implementation must satisfy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from chronopersona.contracts.schemas.agent import AgentOutput, EmbodiedState, EmotionState


class AbstractAgentCore(ABC):
    """Abstract base class for the agent core state machine.

    Implementations must orchestrate the full turn pipeline:
    Input → Intent → Memory → LLM → Output.
    """

    @abstractmethod
    def run_turn(
        self,
        user_input: str,
        embodied_state: Optional[EmbodiedState] = None,
    ) -> AgentOutput:
        """Execute a single conversation turn.

        Args:
            user_input: The raw text input from the user.
            embodied_state: Optional perception snapshot from the 2D environment.

        Returns:
            AgentOutput containing the reply text, optional action plan,
            emotion state, and metadata.

        Raises:
            RuntimeError: If the agent core encounters an unrecoverable error.
        """
        ...

    @abstractmethod
    def switch_persona(self, persona_id: str) -> None:
        """Switch the active persona.

        Args:
            persona_id: Identifier of the persona to activate.

        Raises:
            ValueError: If the persona_id is unknown.
        """
        ...

    @abstractmethod
    def get_emotion_state(self) -> EmotionState:
        """Return the current emotion state of the agent.

        Returns:
            The current EmotionState.
        """
        ...

    @abstractmethod
    def get_memory_summary(self, branch_id: str) -> str:
        """Return a human-readable summary of the memory state for a branch.

        Args:
            branch_id: The branch to summarise.

        Returns:
            A string summary of the memory contents.
        """
        ...
