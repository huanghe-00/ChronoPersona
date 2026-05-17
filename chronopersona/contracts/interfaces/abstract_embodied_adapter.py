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
        """Return current embodied state for the given agent."""

    @abstractmethod
    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        """Execute an action and return the perception result."""

    @abstractmethod
    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        """Return spatial memory records for the agent."""

    @abstractmethod
    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        """Predict a high-level action based on perception and task description."""

    @abstractmethod
    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        """Translate a high-level action token to a low-level command."""
