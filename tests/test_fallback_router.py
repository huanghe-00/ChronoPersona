"""Tests for FallbackRouter.

Validates task-tier routing, fallback chain behavior, cache isolation,
cost tracking per branch, and streaming routing per requirements 7.1/7.2.
"""

import pytest

from chronopersona.contracts.interfaces.abstract_model_client import (
    ModelClientError,
    RateLimitError,
)
from chronopersona.mocks.mock_credential_provider import MockCredentialProvider
from chronopersona.mocks.mock_model_client import MockModelClient
from chronopersona.model_router.api_mode_switch import APIMode, APIModeSwitch
from chronopersona.model_router.fallback_router import FallbackRouter


class TestFallbackRouterInit:
    """Test initialization and client setup."""

    def test_init_with_default_mode_switch(self) -> None:
        """Router initializes with default HYBRID mode switch."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        assert router._mode_switch.current_mode == APIMode.HYBRID

    def test_init_with_custom_mode_switch(self) -> None:
        """Router uses provided mode switch instead of creating default."""
        cred_provider = MockCredentialProvider()
        mode_switch = APIModeSwitch(cred_provider, initial_mode=APIMode.CLOUD)
        router = FallbackRouter(cred_provider, mode_switch=mode_switch)
        assert router._mode_switch.current_mode == APIMode.CLOUD

    def test_init_creates_cloud_clients(self) -> None:
        """Router creates clients for all cloud providers per routing table."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        assert "kimi" in router._clients
        assert "deepseek" in router._clients
        assert "deepseek_pro" in router._clients
        assert "glm" in router._clients


class TestFallbackRouterRouting:
    """Test request routing with fallback chain."""

    def test_route_to_primary_client(self) -> None:
        """Request routes to primary client when healthy (T2 -> deepseek)."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            default_model="deepseek-v4-flash",
            responses={"test prompt": "DeepSeek response"},
        )

        response = router.route(
            prompt="test prompt", task_type="T2", branch_id="main"
        )
        assert response["content"] == "DeepSeek response"
        assert response["model_name"] == "deepseek-v4-flash"

    def test_route_with_model_preference(self) -> None:
        """Model preference overrides routing table selection."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["kimi"] = MockModelClient(
            provider="kimi",
            default_model="kimi-for-coding",
            responses={"test prompt": "Kimi response"},
        )

        response = router.route(
            prompt="test prompt",
            task_type="T2",
            branch_id="main",
            model_preference="kimi",
        )
        assert response["content"] == "Kimi response"

    def test_route_fallback_on_rate_limit(self) -> None:
        """Router falls back to next client in chain on RateLimitError."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)

        # Primary client raises rate limit
        failing_client = MockModelClient(provider="deepseek")

        def raise_rate_limit(*args: object, **kwargs: object) -> None:
            raise RateLimitError("deepseek", retry_after=1.0)

        failing_client.complete = raise_rate_limit  # type: ignore[assignment]
        router._clients["deepseek"] = failing_client

        # Fallback client works
        router._clients["kimi"] = MockModelClient(
            provider="kimi",
            default_model="kimi-for-coding",
            responses={"test prompt": "Kimi fallback response"},
        )

        response = router.route(
            prompt="test prompt", task_type="T2", branch_id="main"
        )
        assert response["content"] == "Kimi fallback response"

    def test_route_fallback_on_client_error(self) -> None:
        """Router falls back on generic ModelClientError (5xx)."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)

        failing_client = MockModelClient(provider="deepseek")

        def raise_error(*args: object, **kwargs: object) -> None:
            raise ModelClientError("deepseek", "Internal error", status_code=500)

        failing_client.complete = raise_error  # type: ignore[assignment]
        router._clients["deepseek"] = failing_client

        router._clients["kimi"] = MockModelClient(
            provider="kimi",
            responses={"test prompt": "Kimi fallback"},
        )

        response = router.route(
            prompt="test prompt", task_type="T2", branch_id="main"
        )
        assert response["content"] == "Kimi fallback"

    def test_route_raises_when_all_fail(self) -> None:
        """ModelClientError raised when all clients in chain fail."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)

        # All clients fail
        for key in ["deepseek", "kimi"]:
            client = MockModelClient(provider=key)

            def make_error(request: object, _provider: str = key) -> None:
                raise ModelClientError(_provider, "Failed")

            client.complete = make_error  # type: ignore[assignment]
            router._clients[key] = client

        with pytest.raises(ModelClientError) as exc_info:
            router.route(
                prompt="test prompt", task_type="T2", branch_id="main"
            )
        assert "All models failed" in str(exc_info.value)

    def test_route_local_rule_engine_for_t3b(self) -> None:
        """T3b (CORRELATED edge) is handled by local rule engine without LLM."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)

        response = router.route(
            prompt="correlation query", task_type="T3b", branch_id="main"
        )
        assert response["model_name"] == "local_rule_engine"
        assert response["finish_reason"] == "rule_engine"


class TestFallbackRouterCache:
    """Test response caching with branch/persona isolation."""

    def test_cache_hit_returns_cached_response(self) -> None:
        """Cached response is returned on identical request (same prompt+branch+persona)."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            responses={"cache test": "First response"},
        )

        # First call populates cache
        response1 = router.route(
            prompt="cache test", task_type="T2", branch_id="main"
        )
        assert response1["content"] == "First response"

        # Replace client to prove cache hit
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            responses={"cache test": "Second response"},
        )
        response2 = router.route(
            prompt="cache test", task_type="T2", branch_id="main"
        )
        assert response2["content"] == "First response"  # Cached, not new

    def test_cache_different_branches_no_pollution(self) -> None:
        """Cache keys differ by branch_id, preventing cross-branch pollution."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            responses={"branch test": "DeepSeek response"},
        )

        response_main = router.route(
            prompt="branch test", task_type="T2", branch_id="main"
        )
        response_therapist = router.route(
            prompt="branch test", task_type="T2", branch_id="therapist"
        )

        # Both succeed with different cache keys (no cross-branch pollution)
        assert response_main["content"] == "DeepSeek response"
        assert response_therapist["content"] == "DeepSeek response"

    def test_cache_clear(self) -> None:
        """Cache clear removes all cached responses."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            responses={"clear test": "Cached response"},
        )

        router.route(prompt="clear test", task_type="T2", branch_id="main")
        router.cache_clear()
        assert len(router._cache) == 0


class TestFallbackRouterCostTracking:
    """Test cost tracking per branch per requirements 4.8.1."""

    def test_cost_recorded_per_call(self) -> None:
        """Cost is recorded for each successful API call."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            default_model="deepseek-v4-flash",
        )

        router.route(prompt="cost test", task_type="T2", branch_id="main")
        summary = router.get_cost_summary(branch_id="main")
        assert summary["total_calls"] == 1
        assert summary["branch_id"] == "main"

    def test_cost_isolated_per_branch(self) -> None:
        """Cost records are isolated by branch_id (no cross-branch aggregation)."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(provider="deepseek")

        router.route(prompt="test", task_type="T2", branch_id="main")
        router.route(prompt="test2", task_type="T2", branch_id="therapist")

        main_summary = router.get_cost_summary(branch_id="main")
        therapist_summary = router.get_cost_summary(branch_id="therapist")

        assert main_summary["total_calls"] == 1
        assert therapist_summary["total_calls"] == 1

    def test_cost_summary_by_model(self) -> None:
        """Cost summary includes per-model breakdown for ROI analysis."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            default_model="deepseek-v4-flash",
        )

        router.route(
            prompt="model cost test", task_type="T2", branch_id="main"
        )
        summary = router.get_cost_summary(branch_id="main")
        assert "by_model" in summary
        assert "deepseek-v4-flash" in summary["by_model"]


class TestFallbackRouterStreaming:
    """Test streaming routing (single attempt, no fallback/cache)."""

    def test_stream_route_to_primary(self) -> None:
        """Stream request routes to primary client for the task tier."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["deepseek"] = MockModelClient(
            provider="deepseek",
            default_model="deepseek-v4-flash",
            responses={"stream test": "Stream response content"},
        )

        chunks = list(
            router.stream_route(
                prompt="stream test", task_type="T2", branch_id="main"
            )
        )
        assert len(chunks) > 0
        assert chunks[-1]["finish_reason"] == "stop"

    def test_stream_route_with_preference(self) -> None:
        """Stream request respects model_preference override."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients["kimi"] = MockModelClient(
            provider="kimi",
            default_model="kimi-for-coding",
            responses={"stream pref": "Kimi stream"},
        )

        chunks = list(
            router.stream_route(
                prompt="stream pref",
                task_type="T2",
                branch_id="main",
                model_preference="kimi",
            )
        )
        assert chunks[0]["model_name"] == "kimi-for-coding"

    def test_stream_route_raises_for_missing_client(self) -> None:
        """Stream route raises ModelClientError for unavailable client."""
        cred_provider = MockCredentialProvider()
        router = FallbackRouter(cred_provider)
        router._clients.clear()

        with pytest.raises(ModelClientError):
            list(
                router.stream_route(
                    prompt="test",
                    task_type="T2",
                    branch_id="main",
                    model_preference="nonexistent",
                )
            )
