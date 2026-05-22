"""Abstract interface for embodied adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chronopersona.contracts.schemas import (
    EmbodiedState,
    LowLevelCommand,
    PerceptionResult,
    SpatialRecord,
)


class AbstractEmbodiedAdapter(ABC):
    """Interface for embodied perception and action adapters."""

    @abstractmethod
    def get_perception(self, agent_id: str) -> EmbodiedState:
        """Return current embodied state for the given agent.

        Args:
            agent_id: Unique identifier of the agent. Must not be empty.

        Returns:
            Current EmbodiedState snapshot.

        Raises:
            ValueError: If agent_id is empty.
        """

    @abstractmethod
    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        """Execute an action and return the perception result.

        Args:
            agent_id: Unique identifier of the agent. Must not be empty.
            action: Action descriptor (robot-type specific).

        Returns:
            PerceptionResult after executing the action.

        Raises:
            ValueError: If agent_id is empty.
        """

    @abstractmethod
    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        """Return spatial memory records for the agent.

        Args:
            agent_id: Unique identifier of the agent. Must not be empty.

        Returns:
            List of SpatialRecord entries.

        Raises:
            ValueError: If agent_id is empty.
        """

    @abstractmethod
    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        """Predict a high-level action based on perception and task description.

        Args:
            percept: Current embodied perception snapshot.
            task_desc: Task description text. Must not be empty.

        Returns:
            Predicted action descriptor.

        Raises:
            ValueError: If task_desc is empty.
        """

    @abstractmethod
    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        """Translate a high-level action token to a low-level command.

        Args:
            action_token: High-level action identifier. Must not be empty.
            params: Additional command parameters.
            robot_type: Target robot type. Must not be empty.

        Returns:
            LowLevelCommand for the target robot.

        Raises:
            ValueError: If action_token or robot_type is empty.
        """
