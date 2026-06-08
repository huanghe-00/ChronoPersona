"""Mock credential provider for testing."""

from typing import Any, Dict, Optional

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    CredentialNotFoundError,
    ICredentialProvider,
)


class MockCredentialProvider(ICredentialProvider):
    """Mock implementation of ICredentialProvider for testing.

    Returns pre-configured credentials without accessing environment
    variables or external config files. Supports branch-scoped key
    lookup for testing cross-branch isolation.

    Attributes:
        _api_keys: Pre-configured API keys per provider.
        _api_bases: Pre-configured API base URLs per provider.
        _extra_headers: Pre-configured extra headers per provider.
        _extra_body: Pre-configured extra body params per provider.
        _refresh_count: Counter for refresh() calls per provider (test helper).
    """

    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        api_bases: Optional[Dict[str, str]] = None,
        extra_headers: Optional[Dict[str, Dict[str, str]]] = None,
        extra_body: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Initialize mock credential provider with test data.

        Args:
            api_keys: API keys per provider. Supports branch-scoped keys
                via "provider:branch_id" format. Default: "mock-key-{provider}".
            api_bases: API base URLs per provider.
                Default: "http://mock-{provider}-api.local/v1".
            extra_headers: Extra headers per provider (default: empty).
            extra_body: Extra body params per provider (default: empty).
        """
        self._api_keys = api_keys or {}
        self._api_bases = api_bases or {}
        self._extra_headers = extra_headers or {}
        self._extra_body = extra_body or {}
        self._refresh_count: Dict[str, int] = {}

    def get_api_key(self, provider: str, branch_id: str) -> str:
        """Return mock API key for a provider.

        Checks branch-scoped key first ("provider:branch_id"),
        then falls back to provider-level key, then default mock key.

        Args:
            provider: Provider identifier.
            branch_id: Branch identifier for scoped key lookup.

        Returns:
            Mock API key string.

        Raises:
            CredentialNotFoundError: If provider has no key and is not
                a known mock provider.
        """
        # Check for branch-scoped key first
        scoped_key = self._api_keys.get(f"{provider}:{branch_id}")
        if scoped_key:
            return scoped_key

        # Fall back to provider-level key
        key = self._api_keys.get(provider)
        if key:
            return key

        # Default mock key for known providers
        if provider in ("kimi", "deepseek", "glm"):
            return f"mock-key-{provider}"

        raise CredentialNotFoundError(
            provider, f"No mock key for provider '{provider}'"
        )

    def get_api_base(self, provider: str) -> str:
        """Return mock API base URL.

        Args:
            provider: Provider identifier.

        Returns:
            Mock base URL string.

        Raises:
            CredentialNotFoundError: If provider is unknown.
        """
        base = self._api_bases.get(provider)
        if base:
            return base

        defaults = {
            "kimi": "http://mock-kimi-api.local/v1",
            "deepseek": "http://mock-deepseek-api.local/v1",
            "glm": "http://mock-glm-api.local/v1",
        }
        default = defaults.get(provider)
        if default:
            return default

        raise CredentialNotFoundError(provider, "No mock base URL")

    def get_extra_headers(self, provider: str) -> Dict[str, str]:
        """Return mock extra headers.

        Args:
            provider: Provider identifier.

        Returns:
            Extra headers dictionary.
        """
        return self._extra_headers.get(provider, {})

    def get_extra_body(self, provider: str) -> Dict[str, Any]:
        """Return mock extra body params.

        Args:
            provider: Provider identifier.

        Returns:
            Extra body params dictionary.
        """
        return self._extra_body.get(provider, {})

    def is_available(self, provider: str) -> bool:
        """Check if mock provider is available.

        Args:
            provider: Provider identifier.

        Returns:
            True for known providers (kimi, deepseek, glm) and
                any provider with explicit key config.
        """
        return provider in ("kimi", "deepseek", "glm") or provider in self._api_keys

    def refresh(self, provider: str) -> None:
        """Record a refresh call for testing verification.

        Does not actually rotate keys (mock has static config),
        but increments a counter for test assertions.

        Args:
            provider: Provider identifier.
        """
        self._refresh_count[provider] = self._refresh_count.get(provider, 0) + 1

    def get_refresh_count(self, provider: str) -> int:
        """Get the number of refresh calls for a provider (test helper).

        Args:
            provider: Provider identifier.

        Returns:
            Number of refresh() calls.
        """
        return self._refresh_count.get(provider, 0)
