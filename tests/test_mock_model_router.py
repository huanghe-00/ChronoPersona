"""Unit tests for MockModelRouter."""

import pytest

from chronopersona.contracts.schemas import CostReport, ModelRequest, ModelResponse
from chronopersona.mocks import MockModelRouter


class TestMockModelRouter:
    """Tests for MockModelRouter."""

    def test_route_returns_model_response(self) -> None:
        """Normal path: route returns ModelResponse with expected fields."""
        router = MockModelRouter()
        req = ModelRequest(prompt="Hello, how are you?")
        resp = router.route(req, branch_id="main")
        assert isinstance(resp, ModelResponse)
        assert resp.content
        assert resp.model_name == "mock-model"
        assert resp.input_tokens == len(req.prompt)
        assert resp.output_tokens == 20

    def test_route_empty_branch_raises(self) -> None:
        """Empty branch_id raises ValueError."""
        router = MockModelRouter()
        req = ModelRequest(prompt="test")
        with pytest.raises(ValueError):
            router.route(req, branch_id="")

    def test_get_cost_summary_returns_cost_report(self) -> None:
        """get_cost_summary returns a CostReport instance."""
        router = MockModelRouter()
        report = router.get_cost_summary(branch_id="main")
        assert isinstance(report, CostReport)

    def test_get_cost_summary_empty_branch_raises(self) -> None:
        """get_cost_summary with empty branch_id raises ValueError."""
        router = MockModelRouter()
        with pytest.raises(ValueError):
            router.get_cost_summary(branch_id="")

    def test_cache_clear_does_not_raise(self) -> None:
        """cache_clear with valid branch_id does not raise."""
        router = MockModelRouter()
        # Should not raise
        router.cache_clear(branch_id="main")

    def test_cache_clear_empty_branch_raises(self) -> None:
        """cache_clear with empty branch_id raises ValueError."""
        router = MockModelRouter()
        with pytest.raises(ValueError):
            router.cache_clear(branch_id="")
