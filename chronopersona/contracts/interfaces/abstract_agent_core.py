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
        branch_id: str,
        embodied_state: Optional[EmbodiedState] = None,
    ) -> AgentOutput:
        """Execute a single conversation turn.

        Args:
            user_input: The raw text input from the user.
            branch_id: Explicit branch identifier for memory isolation.
                Must not be empty.
            embodied_state: Optional perception snapshot from the 2D environment.

        Returns:
            AgentOutput containing the reply text, optional action plan,
            emotion state, and metadata.

        Raises:
            ValueError: If branch_id is empty or user_input is empty.
            RuntimeError: If the agent core encounters an unrecoverable error.
        """
        ...

    @abstractmethod
    def switch_persona(self, persona_id: str, branch_id: str) -> None:
        """Switch the active persona and checkout the corresponding branch.

        Args:
            persona_id: Identifier of the persona to activate.
            branch_id: Target branch to checkout. Must match persona scope.
                Must not be empty.

        Raises:
            ValueError: If persona_id or branch_id is empty.
            LookupError: If the persona or branch does not exist.
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
            branch_id: The branch to summarise. Must not be empty.

        Returns:
            A string summary of the memory contents.

        Raises:
            ValueError: If branch_id is empty.
        """
        ...
