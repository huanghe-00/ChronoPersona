"""Mock implementation of AbstractEmbodiedAdapter."""

from typing import Any, Dict, List

from chronopersona.contracts.interfaces import AbstractEmbodiedAdapter
from chronopersona.contracts.schemas import (
    EmbodiedState,
    LowLevelCommand,
    PerceptionResult,
    SpatialRecord,
)


class MockEmbodiedAdapter(AbstractEmbodiedAdapter):
    """Mock embodied adapter for testing."""

    def get_perception(self, agent_id: str) -> EmbodiedState:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        return EmbodiedState(agent_id=agent_id)

    def execute_action(self, agent_id: str, action: Any) -> PerceptionResult:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        return PerceptionResult(success=True)

    def get_spatial_memory(self, agent_id: str) -> List[SpatialRecord]:
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        return []

    def predict_action(self, percept: EmbodiedState, task_desc: str) -> Any:
        if not task_desc:
            raise ValueError("task_desc must not be empty")
        return {"action_token": "mock_action"}

    def translate_action_token(
        self,
        action_token: str,
        params: Dict[str, Any],
        robot_type: str,
    ) -> LowLevelCommand:
        if not action_token or not robot_type:
            raise ValueError("action_token and robot_type must not be empty")
        return LowLevelCommand(
            robot_type=robot_type,
            command=f"mock_{action_token}",
            params=params,
        )
