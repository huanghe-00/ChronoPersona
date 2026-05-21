"""Mock ActionPlanner for testing."""

from chronopersona.contracts.interfaces import AbstractActionPlanner
from chronopersona.contracts.schemas import ActionPlan, EmotionState


class MockActionPlanner(AbstractActionPlanner):
    """Mock planner returning fixed action plan."""

    def plan(
        self,
        llm_output_text: str,
        emotion_state: EmotionState,
        branch_id: str,
    ) -> ActionPlan:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return ActionPlan(
            action_token="mock_action",
            action_params={"speed": 0.5},
            reasoning="Mock action for testing",
        )
