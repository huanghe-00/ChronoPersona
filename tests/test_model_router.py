"""Unit tests for model router implementations."""

import pytest

from chronopersona.contracts.interfaces import AbstractModelRouter
from chronopersona.contracts.schemas import ModelRequest
from chronopersona.mocks.mock_model_router import MockModelRouter


class TestMockModelRouter:
    """Tests for MockModelRouter ensuring AbstractModelRouter compliance."""

    def test_route_returns_valid_response(self) -> None:
        """T01: route returns ModelResponse with content and usage stats."""
        router: AbstractModelRouter = MockModelRouter()
        req = ModelRequest(prompt="Hello world")
        resp = router.route(req, branch_id="main")
        assert resp.content
        assert resp.input_tokens == len("Hello world")
        assert resp.output_tokens == 20

    def test_route_empty_branch_raises_valueerror(self) -> None:
        """T02: route with empty branch_id raises ValueError."""
        router: AbstractModelRouter = MockModelRouter()
        with pytest.raises(ValueError):
            router.route(ModelRequest(prompt="hi"), branch_id="")

    def test_get_cost_summary_returns_report(self) -> None:
        """T03: get_cost_summary returns CostReport for valid branch."""
        router: AbstractModelRouter = MockModelRouter()
        report = router.get_cost_summary(branch_id="main")
        assert report is not None

    def test_get_cost_summary_empty_branch_raises_valueerror(self) -> None:
        """T04: get_cost_summary with empty branch_id raises ValueError."""
        router: AbstractModelRouter = MockModelRouter()
        with pytest.raises(ValueError):
            router.get_cost_summary(branch_id="")

    def test_cache_clear_empty_branch_raises_valueerror(self) -> None:
        """T05: cache_clear with empty branch_id raises ValueError."""
        router: AbstractModelRouter = MockModelRouter()
        with pytest.raises(ValueError):
            router.cache_clear(branch_id="")
