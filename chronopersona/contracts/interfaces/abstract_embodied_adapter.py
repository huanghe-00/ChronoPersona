"""Abstract Embodied Adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chronopersona.contracts.schemas.agent import EmbodiedState
from chronopersona.contracts.schemas.embodied import (
    LowLevelCommand,
    PerceptionResult,
    SpatialRecord,
)


class AbstractEmbodiedAdapter(ABC):
    """Abstract interface for embodied perception and action translation.

    Implementations must support zero-shot cross-robot transfer via
    Token→Action Bridge pattern. All operations require an explicit
    agent_id; default global agent is strictly prohibited.
    """

    @abstractmethod
    def get_perception(self, agent_id: str) -> EmbodiedState:
        """Retrieve current embodied perception state.

        Args:
            agent_id: Unique agent identifier. Must not be empty.

        Returns:
            EmbodiedState containing position, orientation, and FOV.

        Raises:
            ValueError: If agent_id is empty.
        """
        ...

    @abstractmethod
    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        """Execute a structured action in the embodied environment.

        Args:
            agent_id: Target agent. Must not be empty.
            action: Structured action (typically ActionPlan or dict).

        Returns:
            PerceptionResult describing the outcome.

        Raises:
            ValueError: If agent_id is empty.
            RuntimeError: If the action execution fails.
        """
        ...

    @abstractmethod
    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        """Retrieve spatial memory for an agent.

        Args:
            agent_id: Target agent. Must not be empty.

        Returns:
            List of spatial records.

        Raises:
            ValueError: If agent_id is empty.
        """
        ...

    @abstractmethod
    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        """Predict next action from perception and task description.

        MVA default: LLM-based implementation.
        [VLA-PLACEHOLDER]: Future fine-tuned VLA model replacement.

        Args:
            percept: Current embodied state.
            task_desc: Natural language task description.

        Returns:
            Structured action (Action or ActionPlan).

        Raises:
            ValueError: If task_desc is empty.
        """
        ...

    @abstractmethod
    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        """Translate high-level action token to low-level robot command.

        Args:
            action_token: High-level token (e.g. "approach_gently").
            params: Modulation parameters (speed, proximity, etc.).
            robot_type: Target robot type (grid_2d, ros2_mobile, mujoco).

        Returns:
            LowLevelCommand for the specific robot platform.

        Raises:
            ValueError: If action_token or robot_type is empty.
            LookupError: If action_token is not supported for robot_type.
        """
        ...
