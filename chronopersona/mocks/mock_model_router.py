"""Mock implementation of AbstractModelRouter."""

from chronopersona.contracts.interfaces import AbstractModelRouter
from chronopersona.contracts.schemas import CostReport, ModelRequest, ModelResponse


class MockModelRouter(AbstractModelRouter):
    """Mock model router for testing."""

    def route(self, request: ModelRequest, branch_id: str) -> ModelResponse:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return ModelResponse(
            content=f"[Mock] Response to: {request.prompt[:50]}...",
            model_name="mock-model",
            input_tokens=len(request.prompt),
            output_tokens=20,
        )

    def get_cost_summary(self, branch_id: str) -> CostReport:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        return CostReport()

    def cache_clear(self, branch_id: str) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
