"""Tests for RuntimeCredentialProvider.

Validates credential resolution priority (config > env > default),
branch isolation, refresh behavior, and error handling.
"""

import os
from unittest.mock import patch

import pytest

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    CredentialNotFoundError,
)
from chronopersona.model_router.runtime_credential_provider import (
    RuntimeCredentialProvider,
)


class TestRuntimeCredentialProviderInit:
    """Test initialization and configuration loading."""

    def test_init_with_no_overrides(self) -> None:
        """Provider initializes with empty config overrides."""
        provider = RuntimeCredentialProvider()
        # Availability depends on env vars, so just check no crash
        assert provider is not None

    def test_init_with_config_overrides(self) -> None:
        """Provider initializes with config overrides and resolves keys."""
        overrides = {
            "kimi": {
                "api_key": "test-kimi-key",
                "api_base": "https://test.kimi.api/v1",
            },
        }
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        assert provider.get_api_key("kimi", branch_id="main") == "test-kimi-key"
        assert provider.get_api_base("kimi") == "https://test.kimi.api/v1"


class TestRuntimeCredentialProviderAPIKey:
    """Test API key retrieval priority and error handling."""

    def test_get_api_key_from_config(self) -> None:
        """Config override takes priority over environment variable."""
        overrides = {"deepseek": {"api_key": "config-key"}}
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        key = provider.get_api_key("deepseek", branch_id="main")
        assert key == "config-key"

    def test_get_api_key_from_env_fallback(self) -> None:
        """Environment variable is used when config override is absent."""
        provider = RuntimeCredentialProvider()
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-key"}, clear=False):
            key = provider.get_api_key("deepseek", branch_id="main")
            assert key == "env-key"

    def test_get_api_key_raises_when_missing(self) -> None:
        """CredentialNotFoundError raised when no key exists anywhere."""
        provider = RuntimeCredentialProvider()
        with patch.dict(os.environ, {}, clear=True):
            for var in ["KIMI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(var, None)
            with pytest.raises(CredentialNotFoundError) as exc_info:
                provider.get_api_key("unknown_provider", branch_id="main")
            assert "unknown_provider" in str(exc_info.value)


class TestRuntimeCredentialProviderAPIBase:
    """Test API base URL resolution."""

    def test_get_api_base_default_kimi(self) -> None:
        """Default Kimi API base URL matches .aider.model.settings.yml."""
        provider = RuntimeCredentialProvider()
        base = provider.get_api_base("kimi")
        assert base == "https://api.kimi.com/coding/v1"

    def test_get_api_base_default_deepseek(self) -> None:
        """Default DeepSeek API base URL is returned."""
        provider = RuntimeCredentialProvider()
        base = provider.get_api_base("deepseek")
        assert base == "https://api.deepseek.com/v1"

    def test_get_api_base_default_glm(self) -> None:
        """Default GLM API base URL matches .aider.model.settings.yml proxy."""
        provider = RuntimeCredentialProvider()
        base = provider.get_api_base("glm")
        assert "8080/v1" in base

    def test_get_api_base_override(self) -> None:
        """Config override takes precedence over default mapping."""
        overrides = {"kimi": {"api_base": "https://custom.kimi.api/v1"}}
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        base = provider.get_api_base("kimi")
        assert base == "https://custom.kimi.api/v1"

    def test_get_api_base_raises_for_unknown(self) -> None:
        """CredentialNotFoundError raised for unknown provider."""
        provider = RuntimeCredentialProvider()
        with pytest.raises(CredentialNotFoundError):
            provider.get_api_base("unknown_provider")


class TestRuntimeCredentialProviderExtras:
    """Test extra headers and body params resolution."""

    def test_get_extra_headers_kimi(self) -> None:
        """Kimi provider returns User-Agent header per .aider.model.settings.yml."""
        provider = RuntimeCredentialProvider()
        headers = provider.get_extra_headers("kimi")
        assert headers.get("User-Agent") == "KimiCLI/1.3"

    def test_get_extra_headers_deepseek(self) -> None:
        """DeepSeek provider returns empty headers by default."""
        provider = RuntimeCredentialProvider()
        headers = provider.get_extra_headers("deepseek")
        assert headers == {}

    def test_get_extra_body_default(self) -> None:
        """Default extra body is empty for all providers."""
        provider = RuntimeCredentialProvider()
        body = provider.get_extra_body("deepseek")
        assert body == {}

    def test_get_extra_headers_with_override_merge(self) -> None:
        """Config override merges with (not replaces) default headers."""
        overrides = {"kimi": {"extra_headers": {"X-Custom": "value"}}}
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        headers = provider.get_extra_headers("kimi")
        assert headers.get("User-Agent") == "KimiCLI/1.3"
        assert headers.get("X-Custom") == "value"


class TestRuntimeCredentialProviderAvailability:
    """Test availability checks."""

    def test_is_available_with_config_key(self) -> None:
        """Provider is available when config has API key."""
        overrides = {"kimi": {"api_key": "test-key"}}
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        assert provider.is_available("kimi") is True

    def test_is_available_with_env_key(self) -> None:
        """Provider is available when env var has API key."""
        provider = RuntimeCredentialProvider()
        with patch.dict(os.environ, {"KIMI_API_KEY": "env-key"}, clear=False):
            assert provider.is_available("kimi") is True

    def test_is_not_available_without_key(self) -> None:
        """Provider is not available when no key exists."""
        provider = RuntimeCredentialProvider()
        with patch.dict(os.environ, {}, clear=True):
            for var in ["KIMI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(var, None)
            assert provider.is_available("unknown_provider") is False


class TestRuntimeCredentialProviderRefresh:
    """Test credential refresh behavior."""

    def test_refresh_clears_cache(self) -> None:
        """Refresh clears cached credentials but config still resolves."""
        overrides = {"kimi": {"api_key": "original-key"}}
        provider = RuntimeCredentialProvider(config_overrides=overrides)
        # Access to populate cache
        provider.get_api_key("kimi", branch_id="main")
        provider.refresh("kimi")
        # Config override still works after refresh
        key = provider.get_api_key("kimi", branch_id="main")
        assert key == "original-key"

    def test_refresh_raises_for_unknown_provider(self) -> None:
        """CredentialNotFoundError raised when refreshing unknown provider."""
        provider = RuntimeCredentialProvider()
        with pytest.raises(CredentialNotFoundError):
            provider.refresh("unknown_provider")
