"""LLM generation node."""

from chronopersona.contracts.interfaces import AbstractModelRouter
from chronopersona.contracts.schemas import ModelRequest, ModelResponse


class LLMNode:
    """Routes prompt to model and returns response."""

    def __init__(self, model_router: AbstractModelRouter) -> None:
        self._model_router = model_router

    def generate(self, prompt: str, branch_id: str) -> ModelResponse:
        """Generate response from LLM via model router."""
        request = ModelRequest(prompt=prompt)
        return self._model_router.route(request, branch_id)
